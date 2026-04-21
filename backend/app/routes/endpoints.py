import logging
import os
import time

from flask import jsonify, request
from globus_compute_sdk.errors import TaskPending

from app import app, g_database
from app.utils.data_prep import (
    endpoint_initialization_status,
    globus_compute_wrapped_run,
    load_accounts_partitions,
    register_all_endpoints,
)
from app.utils.functions import check_diamond_work_path, create_diamond_dir
from app.utils.login_flow import initialize_globus_compute_client


def _wait_for_result(client, task_id, max_attempts=30, sleep_seconds=2):
    for _ in range(max_attempts):
        try:
            return client.get_result(task_id)
        except TaskPending:
            time.sleep(sleep_seconds)
    raise TimeoutError(f"Task {task_id} still pending after {max_attempts * sleep_seconds}s")

logger = logging.getLogger(__name__)


@app.route("/api/register_all_endpoints", methods=["POST"])
def diamond_register_all_endpoints():
    globus_compute_client = initialize_globus_compute_client()
    all_endpoints = register_all_endpoints(globus_compute_client, g_database, logger)
    return jsonify({"status": "success", "endpoints": all_endpoints}), 200


@app.route("/api/load_accounts_partitions", methods=["POST"])
def diamond_load_accounts_partitions():
    endpoint_uuid = (request.get_json(silent=True) or {}).get("endpoint_uuid")
    if not endpoint_uuid:
        return jsonify({"error": "endpoint_uuid is required"}), 400
    globus_compute_client = initialize_globus_compute_client()
    account_list, partition_list = load_accounts_partitions(
        endpoint_uuid, g_database, logger, globus_compute_client
    )
    return jsonify({
        "status": "success",
        "account_list": account_list,
        "partition_list": partition_list,
    })


@app.route("/api/set_work_path", methods=["POST"])
def set_work_path():
    data = request.get_json(silent=True) or {}
    endpoint_uuid = data.get("endpoint_uuid")
    work_path = data.get("work_path")

    if not endpoint_uuid or not work_path:
        return jsonify({"error": "endpoint_uuid and work_path are required"}), 400

    hpc_dir = work_path if work_path.endswith("hpc_agent") else os.path.join(work_path, "hpc_agent")
    log_dir = os.path.join(hpc_dir, "logs")

    try:
        globus_compute_client = initialize_globus_compute_client()
        user_cfg = g_database.get_endpoint_user_config(endpoint_uuid=endpoint_uuid)

        check_func_id = globus_compute_client.register_function(check_diamond_work_path)
        check_task_id = globus_compute_wrapped_run(
            globus_compute_client,
            endpoint_id=endpoint_uuid,
            function_id=check_func_id,
            user_endpoint_config=user_cfg,
            kwargs={"diamond_work_path": work_path},
        )

        result = _wait_for_result(globus_compute_client, check_task_id)
        if str(getattr(result, "stdout", result)).strip() == "0":
            return jsonify({"error": "Path does not exist or is not writable on the remote endpoint"}), 400

        create_func_id = globus_compute_client.register_function(create_diamond_dir)
        create_task_id = globus_compute_wrapped_run(
            globus_compute_client,
            endpoint_id=endpoint_uuid,
            function_id=create_func_id,
            user_endpoint_config=user_cfg,
            kwargs={"diamond_dir": hpc_dir, "diamond_log_dir": log_dir},
        )
        _wait_for_result(globus_compute_client, create_task_id)

        g_database.save_diamond_dir(endpoint_uuid=endpoint_uuid, diamond_dir=hpc_dir)
        return jsonify({"status": "success", "hpc_dir": hpc_dir})

    except TimeoutError as exc:
        logger.error("set_work_path timed out for %s: %s", endpoint_uuid, exc)
        return jsonify({"error": str(exc)}), 504
    except Exception as exc:
        logger.exception("set_work_path failed for %s", endpoint_uuid)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/endpoint_overview", methods=["GET"])
def get_endpoint_overview():
    globus_compute_client = initialize_globus_compute_client()
    return jsonify(endpoint_initialization_status(globus_compute_client, g_database))


@app.route("/api/list_all_endpoints", methods=["GET"])
def list_all_endpoints():
    endpoints = g_database.get_endpoints()
    result = sorted([{
        "endpoint_uuid": e.endpoint_uuid,
        "endpoint_name": e.endpoint_name,
        "endpoint_host": e.endpoint_host,
        "endpoint_status": e.endpoint_status,
        "diamond_dir": e.diamond_dir,
        "is_managed": e.is_managed,
        "partitions": e.partitions or [],
        "accounts": e.accounts or [],
    } for e in endpoints], key=lambda x: x["endpoint_name"])
    return jsonify(result)


@app.route("/api/list_active_managed_endpoints", methods=["GET"])
def list_active_managed_endpoints():
    endpoints = g_database.get_managed_endpoints()
    return jsonify([{
        "endpoint_uuid": e.endpoint_uuid,
        "endpoint_name": e.endpoint_name,
        "endpoint_host": e.endpoint_host,
        "endpoint_status": e.endpoint_status,
        "diamond_dir": e.diamond_dir,
        "is_managed": e.is_managed,
        "partitions": e.partitions or [],
        "accounts": e.accounts or [],
    } for e in endpoints if e.endpoint_status == "online"])


@app.route("/api/manage_endpoint/<endpoint_uuid>", methods=["PUT"])
def update_endpoint_managed_status(endpoint_uuid):
    data = request.get_json(silent=True) or {}
    is_managed = data.get("is_managed")
    if not isinstance(is_managed, bool):
        return jsonify({"error": "is_managed must be a boolean"}), 400
    g_database.update_endpoint_managed_status(endpoint_uuid=endpoint_uuid, is_managed=is_managed)
    return jsonify({"status": "success", "is_managed": is_managed})


@app.route("/api/user_endpoint_config/<endpoint_uuid>", methods=["GET"])
def get_endpoint_config(endpoint_uuid):
    cfg = g_database.get_endpoint_user_config(endpoint_uuid=endpoint_uuid)
    return jsonify({"endpoint_uuid": endpoint_uuid, "user_endpoint_config": cfg})


@app.route("/api/user_endpoint_config/<endpoint_uuid>", methods=["PUT"])
def update_endpoint_config(endpoint_uuid):
    data = request.get_json(silent=True) or {}
    cfg = data.get("user_endpoint_config")
    g_database.update_endpoint_user_config(endpoint_uuid=endpoint_uuid, user_endpoint_config=cfg)
    return jsonify({"status": "success", "user_endpoint_config": cfg})


@app.route("/api/get_diamond_dir", methods=["GET"])
def get_diamond_dir():
    endpoint_uuid = request.args.get("endpoint_uuid")
    diamond_dir = g_database.get_diamond_dir(endpoint_uuid=endpoint_uuid)
    return jsonify({"diamond_dir": diamond_dir})
