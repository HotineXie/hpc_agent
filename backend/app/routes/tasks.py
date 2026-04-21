import os
import re
import logging
from flask import jsonify, request
from sqlalchemy import func
from app import app, g_database
from app.task_runtime import submit_batch_script_task, refresh_task_statuses, read_remote_task_log, TaskSubmissionError
from app.utils.scripts_render import render_submit_task_script
from app.database import node_hours
from app.models import Task, Endpoint

logger = logging.getLogger(__name__)

_TIME_PATTERN = re.compile(r"^(\d+):(\d{2}):(\d{2})$")


def _parse_walltime_seconds(time_str: str) -> int:
    m = _TIME_PATTERN.match(time_str or "")
    if not m:
        return 0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))


@app.route("/api/submit_task", methods=["POST"])
def submit_task():
    data = request.get_json(silent=True) or {}

    endpoint_id = data.get("endpoint_id") or data.get("endpoint")
    task_name = data.get("task_name") or data.get("taskName")
    partition = data.get("partition")
    account = data.get("account")
    time_duration = data.get("time_duration")
    raw_nodes = data.get("num_of_nodes", 1)
    task_command = data.get("task_command", "")
    slurm_options = data.get("slurm_options", "")
    reservation = data.get("reservation", "")
    raw_script = data.get("raw_script")
    agent_run_id = data.get("agent_run_id")

    if not endpoint_id:
        return jsonify({"error": "endpoint_id is required"}), 400
    if not task_name:
        return jsonify({"error": "task_name is required"}), 400
    try:
        num_of_nodes = int(raw_nodes)
        if num_of_nodes < 1:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "num_of_nodes must be a positive integer"}), 400

    walltime_seconds = _parse_walltime_seconds(time_duration or "")
    allowed, remaining, budget = g_database.check_node_hour_budget(
        endpoint_id, num_of_nodes, walltime_seconds
    )
    if not allowed:
        return jsonify({
            "error": "Node hour budget exceeded",
            "remaining_node_hours": round(remaining, 2),
            "budget_period": budget.period,
        }), 429

    location = g_database.get_diamond_dir(endpoint_uuid=endpoint_id) or "/tmp"
    stdout_path = os.path.join(location, "logs", f"{task_name}.stdout")
    stderr_path = os.path.join(location, "logs", f"{task_name}.stderr")

    if raw_script:
        submit_script = raw_script
    else:
        if not all([partition, account, time_duration]):
            return jsonify({"error": "partition, account, time_duration are required"}), 400
        if reservation and not reservation.startswith("--reservation="):
            reservation = "--reservation=" + reservation
        submit_script = render_submit_task_script(
            task_name=task_name,
            location=location,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            time_duration=time_duration,
            partition=partition,
            account=account,
            reservation=reservation,
            num_of_nodes=num_of_nodes,
            task_command=task_command,
            slurm_options=slurm_options,
        )

    try:
        result = submit_batch_script_task(
            endpoint_id=endpoint_id,
            task_name=task_name,
            submit_script=submit_script,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            agent_run_id=agent_run_id,
        )
    except TaskSubmissionError as exc:
        return jsonify(exc.to_response_payload()), exc.http_status

    g_database.record_usage(
        task_id=result["task_id"],
        endpoint_uuid=endpoint_id,
        nodes=num_of_nodes,
        walltime_seconds_requested=walltime_seconds,
        node_hours_estimated=node_hours(num_of_nodes, walltime_seconds),
    )

    return jsonify({"status": "success", **result}), 200


@app.route("/api/get_task_status", methods=["GET"])
def get_task_status():
    try:
        tasks = refresh_task_statuses()
    except Exception:
        logger.exception("Failed to refresh task statuses")
        tasks = g_database.load_tasks()

    return jsonify([{
        "task_id": t.task_id,
        "batch_job_id": t.batch_job_id,
        "task_name": t.task_name,
        "task_status": t.task_status,
        "task_create_time": t.task_create_time.isoformat() if t.task_create_time else None,
        "compute_endpoint_id": t.compute_endpoint_id,
        "stdout_path": t.stdout_path,
        "stderr_path": t.stderr_path,
        "agent_run_id": t.agent_run_id,
    } for t in tasks])


@app.route("/api/get_task_log", methods=["GET"])
def get_task_log_route():
    task_id = request.args.get("task_id")
    if not task_id:
        return jsonify({"error": "task_id is required"}), 400

    task = g_database.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    if not task.stdout_path:
        return jsonify({"content": "", "is_complete": False})

    try:
        return jsonify(read_remote_task_log(
            endpoint_id=task.compute_endpoint_id,
            log_path=task.stdout_path,
        ))
    except Exception:
        logger.exception("Failed to read log for task %s", task_id)
        return jsonify({"error": "Failed to read log"}), 500


@app.route("/api/delete_task", methods=["POST"])
def delete_task():
    data = request.get_json(silent=True) or {}
    task_id = data.get("task_id")
    if not task_id:
        return jsonify({"error": "task_id is required"}), 400
    g_database.delete_task(task_id)
    return jsonify({"status": "success"})


@app.route("/api/stats", methods=["GET"])
def get_stats():
    from app.models import Agent, AgentRun
    from app import db
    task_counts = dict(db.session.query(Task.task_status, func.count()).group_by(Task.task_status).all())
    return jsonify({
        "total_tasks": sum(task_counts.values()),
        "running_tasks": task_counts.get("RUNNING", 0),
        "completed_tasks": task_counts.get("COMPLETED", 0),
        "failed_tasks": task_counts.get("FAILED", 0),
        "total_endpoints": Endpoint.query.count(),
        "managed_endpoints": Endpoint.query.filter_by(is_managed=True).count(),
        "total_agents": Agent.query.count(),
        "total_runs": AgentRun.query.count(),
    })


@app.route("/api/healthcheck", methods=["GET"])
def healthcheck():
    return jsonify({"status": "ok"})
