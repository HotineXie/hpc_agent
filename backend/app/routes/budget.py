from flask import jsonify, request
from app import app, g_database
from app.database import node_hours


@app.route("/api/budget", methods=["GET"])
def get_budget():
    endpoint_uuid = request.args.get("endpoint_uuid")
    budget = g_database.get_budget(endpoint_uuid=endpoint_uuid)
    if not budget:
        return jsonify({"budget": None})

    period = budget.period
    used = g_database.get_usage_in_period(period=period, endpoint_uuid=endpoint_uuid)
    return jsonify({
        "budget": {
            "id": budget.id,
            "endpoint_uuid": budget.endpoint_uuid,
            "max_node_hours": budget.max_node_hours,
            "period": period,
            "used_node_hours": round(used, 4),
            "remaining_node_hours": round(max(0, budget.max_node_hours - used), 4),
        }
    })


@app.route("/api/budget", methods=["POST"])
def set_budget():
    data = request.get_json(silent=True) or {}
    max_node_hours = data.get("max_node_hours")
    period = data.get("period", "monthly")
    endpoint_uuid = data.get("endpoint_uuid")

    if max_node_hours is None or not isinstance(max_node_hours, (int, float)) or max_node_hours <= 0:
        return jsonify({"error": "max_node_hours must be a positive number"}), 400
    if period not in ("daily", "weekly", "monthly"):
        return jsonify({"error": "period must be daily, weekly, or monthly"}), 400

    budget = g_database.set_budget(
        max_node_hours=float(max_node_hours),
        period=period,
        endpoint_uuid=endpoint_uuid,
    )
    return jsonify({
        "id": budget.id,
        "endpoint_uuid": budget.endpoint_uuid,
        "max_node_hours": budget.max_node_hours,
        "period": budget.period,
    }), 200


@app.route("/api/budget", methods=["DELETE"])
def delete_budget():
    endpoint_uuid = request.args.get("endpoint_uuid")
    g_database.delete_budget(endpoint_uuid=endpoint_uuid)
    return jsonify({"status": "success"})


@app.route("/api/budget/check", methods=["POST"])
def check_budget():
    data = request.get_json(silent=True) or {}
    endpoint_id = data.get("endpoint_id")
    nodes = int(data.get("nodes", 1))
    walltime_seconds = int(data.get("walltime_seconds", 0))

    estimated = node_hours(nodes, walltime_seconds)
    allowed, remaining, budget = g_database.check_node_hour_budget(
        endpoint_id, nodes, walltime_seconds
    )

    if not allowed:
        return jsonify({
            "allowed": False,
            "reason": "Budget exceeded",
            "estimated_node_hours": round(estimated, 4),
            "remaining_node_hours": round(remaining, 4),
            "period": budget.period,
        })

    return jsonify({"allowed": True, "estimated_node_hours": round(estimated, 4)})


@app.route("/api/budget/usage", methods=["GET"])
def get_usage():
    period = request.args.get("period", "monthly")
    endpoint_uuid = request.args.get("endpoint_uuid")

    usages = g_database.list_usage(period=period, endpoint_uuid=endpoint_uuid)
    total_estimated = sum(u.node_hours_estimated for u in usages)
    total_actual = sum(u.node_hours_actual or 0 for u in usages)

    return jsonify({
        "period": period,
        "total_estimated_node_hours": round(total_estimated, 4),
        "total_actual_node_hours": round(total_actual, 4),
        "records": [{
            "task_id": u.task_id,
            "endpoint_uuid": u.endpoint_uuid,
            "nodes": u.nodes,
            "walltime_seconds_requested": u.walltime_seconds_requested,
            "node_hours_estimated": round(u.node_hours_estimated, 4),
            "node_hours_actual": round(u.node_hours_actual, 4) if u.node_hours_actual else None,
            "recorded_at": u.recorded_at.isoformat() if u.recorded_at else None,
        } for u in usages],
    })
