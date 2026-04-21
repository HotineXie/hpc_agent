import uuid
from datetime import datetime
from app import db


class Task(db.Model):
    __tablename__ = "task"
    task_id = db.Column(db.String, primary_key=True)
    batch_job_id = db.Column(db.String)
    task_name = db.Column(db.String)
    task_status = db.Column(db.String, index=True)
    task_create_time = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    stdout_path = db.Column(db.String)
    stderr_path = db.Column(db.String)
    log_path = db.Column(db.String)
    compute_endpoint_id = db.Column(db.String, index=True)
    checkpoint_path = db.Column(db.String)
    agent_run_id = db.Column(db.String, db.ForeignKey("agent_run.id"), nullable=True, index=True)


class Endpoint(db.Model):
    __tablename__ = "endpoint"
    endpoint_uuid = db.Column(db.String, primary_key=True)
    endpoint_name = db.Column(db.String, nullable=False)
    endpoint_host = db.Column(db.String, nullable=False)
    endpoint_status = db.Column(db.String, nullable=False)
    partitions = db.Column(db.JSON, nullable=True)
    accounts = db.Column(db.JSON, nullable=True)
    diamond_dir = db.Column(db.String, nullable=True)
    is_managed = db.Column(db.Boolean, default=False, index=True)
    user_endpoint_config = db.Column(db.JSON, nullable=True)


class Agent(db.Model):
    __tablename__ = "agent"
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String, nullable=False)
    system_prompt = db.Column(db.Text)
    model = db.Column(db.String, default="claude-sonnet-4-6")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AgentRun(db.Model):
    __tablename__ = "agent_run"
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = db.Column(db.String, db.ForeignKey("agent.id"), index=True)
    task = db.Column(db.Text)
    status = db.Column(db.String, default="pending", index=True)
    log = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    endpoint_id = db.Column(db.String, nullable=True)


class NodeHourBudget(db.Model):
    __tablename__ = "node_hour_budget"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    endpoint_uuid = db.Column(db.String, nullable=True, index=True)
    max_node_hours = db.Column(db.Float, nullable=False)
    period = db.Column(db.String, default="monthly")


class NodeHourUsage(db.Model):
    __tablename__ = "node_hour_usage"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.String, db.ForeignKey("task.task_id"), index=True)
    endpoint_uuid = db.Column(db.String, index=True)
    nodes = db.Column(db.Integer, default=1)
    walltime_seconds_requested = db.Column(db.Integer, default=0)
    walltime_seconds_actual = db.Column(db.Integer, nullable=True)
    node_hours_estimated = db.Column(db.Float, default=0.0)
    node_hours_actual = db.Column(db.Float, nullable=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
