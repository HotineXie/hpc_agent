from datetime import datetime
from flask import jsonify, request
from app import app, g_database


@app.route("/api/agents", methods=["GET"])
def list_agents():
    agents = g_database.list_agents()
    return jsonify([{
        "id": a.id,
        "name": a.name,
        "system_prompt": a.system_prompt,
        "model": a.model,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    } for a in agents])


@app.route("/api/agents", methods=["POST"])
def create_agent():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    system_prompt = data.get("system_prompt", "").strip()
    model = data.get("model", "claude-sonnet-4-6")

    if not name:
        return jsonify({"error": "name is required"}), 400

    agent = g_database.save_agent(name=name, system_prompt=system_prompt, model=model)
    return jsonify({
        "id": agent.id,
        "name": agent.name,
        "system_prompt": agent.system_prompt,
        "model": agent.model,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
    }), 201


@app.route("/api/agents/<agent_id>", methods=["GET"])
def get_agent(agent_id):
    agent = g_database.get_agent(agent_id)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404
    return jsonify({
        "id": agent.id,
        "name": agent.name,
        "system_prompt": agent.system_prompt,
        "model": agent.model,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
    })


@app.route("/api/agents/<agent_id>", methods=["PUT"])
def update_agent(agent_id):
    data = request.get_json(silent=True) or {}
    agent = g_database.update_agent(
        agent_id,
        name=data.get("name"),
        system_prompt=data.get("system_prompt"),
        model=data.get("model"),
    )
    if not agent:
        return jsonify({"error": "Agent not found"}), 404
    return jsonify({
        "id": agent.id,
        "name": agent.name,
        "system_prompt": agent.system_prompt,
        "model": agent.model,
    })


@app.route("/api/agents/<agent_id>", methods=["DELETE"])
def delete_agent(agent_id):
    g_database.delete_agent(agent_id)
    return jsonify({"status": "success"})


@app.route("/api/runs", methods=["GET"])
def list_runs():
    agent_id = request.args.get("agent_id")
    runs = g_database.list_agent_runs(agent_id=agent_id)
    return jsonify([_run_to_dict(r) for r in runs])


@app.route("/api/runs", methods=["POST"])
def create_run():
    data = request.get_json(silent=True) or {}
    agent_id = data.get("agent_id")
    task = data.get("task", "").strip()
    endpoint_id = data.get("endpoint_id")

    if not agent_id or not task:
        return jsonify({"error": "agent_id and task are required"}), 400

    agent = g_database.get_agent(agent_id)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404

    run = g_database.create_agent_run(agent_id=agent_id, task=task, endpoint_id=endpoint_id)
    return jsonify(_run_to_dict(run)), 201


@app.route("/api/runs/<run_id>", methods=["GET"])
def get_run(run_id):
    run = g_database.get_agent_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    return jsonify(_run_to_dict(run))


@app.route("/api/runs/<run_id>", methods=["PATCH"])
def update_run(run_id):
    data = request.get_json(silent=True) or {}
    completed_at = None
    if data.get("status") in ("completed", "failed"):
        completed_at = datetime.utcnow()
    run = g_database.update_agent_run(
        run_id,
        status=data.get("status"),
        log=data.get("log"),
        completed_at=completed_at,
    )
    if not run:
        return jsonify({"error": "Run not found"}), 404
    return jsonify(_run_to_dict(run))


def _run_to_dict(run):
    return {
        "id": run.id,
        "agent_id": run.agent_id,
        "task": run.task,
        "status": run.status,
        "log": run.log,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "endpoint_id": run.endpoint_id,
    }
