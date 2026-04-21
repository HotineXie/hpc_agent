import logging
import re
import threading
import time
from datetime import datetime

from globus_compute_sdk.errors import TaskPending

from app import g_database
from app.utils.data_prep import globus_compute_wrapped_run
from app.utils.functions import fetch_task_status, get_task_log, run_submit_script
from app.utils.login_flow import initialize_globus_compute_client

logger = logging.getLogger(__name__)

SBATCH_JOB_ID_PATTERN = re.compile(r"Submitted batch job (\d+)")

SLURM_STATE_MAPPING = {
    "COMPLETING": "COMPLETED",
    "COMPLETED+": "COMPLETED",
    "COMPLETED": "COMPLETED",
    "CANCELED": "COMPLETED",
    "FAILED": "FAILED",
    "TIMEOUT": "FAILED",
    "OUT_OF_MEMORY": "FAILED",
    "RUNNING": "RUNNING",
    "PENDING": "PENDING",
}
TERMINAL_STATES = ["COMPLETED", "COMPLETING", "FAILED", "MISSING"]

# In-memory TTL cache (thread-safe, replaces Redis for single-instance use)
_status_cache: dict = {}
_cache_lock = threading.Lock()
STATUS_CACHE_TTL = 30


class TaskSubmissionError(Exception):
    def __init__(self, error, *, http_status=500, payload=None):
        super().__init__(error)
        self.error = error
        self.http_status = http_status
        self.payload = payload or {}

    def to_response_payload(self):
        return {"error": self.error, **self.payload}


def _cache_get(key):
    with _cache_lock:
        entry = _status_cache.get(key)
        if entry:
            data, expire = entry
            if time.time() < expire:
                return data
            del _status_cache[key]
        return None


def _cache_set(key, data, ttl=STATUS_CACHE_TTL):
    now = time.time()
    with _cache_lock:
        _status_cache[key] = (data, now + ttl)
        # Evict expired entries to prevent unbounded growth
        expired = [k for k, (_, exp) in _status_cache.items() if exp < now]
        for k in expired:
            del _status_cache[k]


def _cache_delete(key):
    with _cache_lock:
        _status_cache.pop(key, None)


def _wait_for_compute_result(globus_compute_client, task_id, *, max_attempts=12):
    for attempt in range(max_attempts):
        try:
            return globus_compute_client.get_result(task_id)
        except TaskPending:
            time.sleep(attempt)
        except Exception as exc:
            raise TaskSubmissionError(
                "Failed to submit job - could not fetch results from endpoint",
                payload={"task_id": task_id, "details": str(exc)},
            ) from exc
    raise TaskSubmissionError(
        "Failed to submit job - task timed out",
        payload={"task_id": task_id},
    )


def _extract_slurm_batch_job_id(submit_result):
    if isinstance(submit_result, dict):
        stdout = submit_result.get("stdout", "")
        stderr = submit_result.get("stderr", "")
        returncode = submit_result.get("returncode", None)
    else:
        stdout = getattr(submit_result, "stdout", "")
        stderr = getattr(submit_result, "stderr", "")
        returncode = getattr(submit_result, "returncode", None)

    if returncode not in (None, 0):
        msg = "Failed to submit job - sbatch returned non-zero exit code"
        if stderr:
            msg = f"{msg}: {stderr}"
        raise TaskSubmissionError(msg, payload={"stdout": stdout, "stderr": stderr, "returncode": returncode})

    match = SBATCH_JOB_ID_PATTERN.search(stdout)
    if not match:
        msg = "Failed to submit job - could not parse SLURM job ID"
        if stderr:
            msg = f"{msg}: {stderr}"
        raise TaskSubmissionError(msg, payload={"stdout": stdout, "stderr": stderr})

    return match.group(1)


def submit_batch_script_task(*, endpoint_id, task_name, submit_script,
                              stdout_path, stderr_path, log_path="",
                              checkpoint_path="", agent_run_id=None):
    globus_compute_client = initialize_globus_compute_client()
    user_endpoint_config = g_database.get_endpoint_user_config(endpoint_uuid=endpoint_id)

    function_id = globus_compute_client.register_function(run_submit_script)

    try:
        task_id = globus_compute_wrapped_run(
            globus_compute_client,
            endpoint_id=endpoint_id,
            function_id=function_id,
            user_endpoint_config=user_endpoint_config,
            kwargs={"submit_script": submit_script},
        )
    except Exception as exc:
        raise TaskSubmissionError(
            "Failed to submit task to Globus Compute",
            http_status=getattr(exc, "http_status", 500),
            payload={"details": str(exc)},
        ) from exc

    submit_result = _wait_for_compute_result(globus_compute_client, task_id)
    batch_job_id = _extract_slurm_batch_job_id(submit_result)
    logger.info("Task %s mapped to SLURM job %s", task_id, batch_job_id)

    g_database.save_task(
        task_id=task_id,
        batch_job_id=batch_job_id,
        task_name=task_name,
        task_status="PENDING",
        task_create_time=datetime.now(),
        log_path=log_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        compute_endpoint_id=endpoint_id,
        checkpoint_path=checkpoint_path,
        agent_run_id=agent_run_id,
    )

    return {
        "task_id": task_id,
        "batch_job_id": batch_job_id,
        "task_name": task_name,
        "stdout_path": stdout_path,
        "stderr_path": stderr_path,
    }


def refresh_task_statuses():
    globus_compute_client = initialize_globus_compute_client()
    cache_key = "task_status_refresh"
    runtime_record = _cache_get(cache_key)

    tasks = g_database.load_tasks()
    if runtime_record is None:
        pending_tasks = [t for t in tasks if t.task_status not in TERMINAL_STATES]
        if not pending_tasks:
            return tasks

        status_func_id = globus_compute_client.register_function(fetch_task_status)
        records = []
        for task in pending_tasks:
            user_cfg = g_database.get_endpoint_user_config(endpoint_uuid=task.compute_endpoint_id)
            try:
                status_task_id = globus_compute_wrapped_run(
                    globus_compute_client,
                    endpoint_id=task.compute_endpoint_id,
                    function_id=status_func_id,
                    user_endpoint_config=user_cfg,
                    kwargs={"batch_job_id": task.batch_job_id},
                )
                records.append({"task_id": task.task_id, "status_task_id": status_task_id})
            except Exception as exc:
                logger.warning("Failed to submit status check for task %s: %s", task.task_id, exc)

        if records:
            _cache_set(cache_key, records)
    else:
        pending = []
        for record in runtime_record:
            try:
                result = globus_compute_client.get_task(record["status_task_id"])
            except Exception:
                continue
            if result.get("pending", False):
                pending.append(record)
                continue
            try:
                status_result = globus_compute_client.get_result(record["status_task_id"])
                if isinstance(status_result, dict):
                    raw_status = status_result.get("stdout", "").strip()
                else:
                    raw_status = getattr(status_result, "stdout", "").strip()
                new_status = None
                if raw_status:
                    new_status = SLURM_STATE_MAPPING.get(raw_status, "MISSING")
                else:
                    prev = g_database.get_task_status(record["task_id"])
                    if prev in ["RUNNING", "COMPLETING"]:
                        new_status = "COMPLETED"
                if new_status:
                    g_database.update_task_status(record["task_id"], new_status)
                    logger.info("Updated task %s to %s", record["task_id"], new_status)
            except Exception as exc:
                logger.warning("Failed to get status for %s: %s", record["task_id"], exc)

        if pending:
            _cache_set(cache_key, pending)
        else:
            _cache_delete(cache_key)

    return g_database.load_tasks()


def read_remote_task_log(*, endpoint_id, log_path, max_attempts=5, retry_sleep_seconds=2):
    if not log_path:
        return {"content": "", "is_complete": False}

    globus_compute_client = initialize_globus_compute_client()
    get_task_log_func_id = globus_compute_client.register_function(get_task_log)
    user_cfg = g_database.get_endpoint_user_config(endpoint_uuid=endpoint_id)
    log_task_id = globus_compute_wrapped_run(
        globus_compute_client,
        endpoint_id=endpoint_id,
        function_id=get_task_log_func_id,
        user_endpoint_config=user_cfg,
        kwargs={"log_file_path": log_path},
    )

    fallback = {"content": "Failed to load log within time limit", "is_complete": False}
    for _ in range(max_attempts):
        try:
            result = globus_compute_client.get_result(log_task_id)
        except TaskPending:
            time.sleep(retry_sleep_seconds)
            continue
        except Exception:
            logger.exception("Failed to read log %s", log_path)
            return fallback
        if isinstance(result, dict):
            return {"content": result.get("content", ""), "is_complete": bool(result.get("is_complete", False))}
        return {"content": str(result), "is_complete": False}
    return fallback
