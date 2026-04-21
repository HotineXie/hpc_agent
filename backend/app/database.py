from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models import Task, Endpoint, Agent, AgentRun, NodeHourBudget, NodeHourUsage


def _period_start(period: str) -> datetime:
    now = datetime.utcnow()
    if period == "daily":
        return now - timedelta(days=1)
    if period == "weekly":
        return now - timedelta(weeks=1)
    return now - timedelta(days=30)


def node_hours(nodes: int, walltime_seconds: int) -> float:
    return (nodes * walltime_seconds) / 3600.0


class Database:
    # ── Task ──────────────────────────────────────────────────────────────────

    def save_task(self, task_id, batch_job_id, task_name, task_status,
                  task_create_time, stdout_path, stderr_path, log_path,
                  compute_endpoint_id, checkpoint_path="", agent_run_id=None):
        task = Task(
            task_id=task_id,
            batch_job_id=batch_job_id,
            task_name=task_name,
            task_status=task_status,
            task_create_time=task_create_time,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            log_path=log_path,
            compute_endpoint_id=compute_endpoint_id,
            checkpoint_path=checkpoint_path,
            agent_run_id=agent_run_id,
        )
        db.session.add(task)
        db.session.commit()
        return task

    def get_task(self, task_id):
        return db.session.get(Task, task_id)

    def load_tasks(self):
        return Task.query.order_by(Task.task_create_time.desc()).all()

    def update_task_status(self, task_id, status):
        task = db.session.get(Task, task_id)
        if task:
            task.task_status = status
            db.session.commit()

    def get_task_status(self, task_id):
        task = db.session.get(Task, task_id)
        return task.task_status if task else None

    def delete_task(self, task_id):
        task = db.session.get(Task, task_id)
        if task:
            db.session.delete(task)
            db.session.commit()

    # ── Endpoint ──────────────────────────────────────────────────────────────

    def save_endpoint(self, endpoint_uuid, endpoint_name, endpoint_host,
                      endpoint_status, partitions=None, accounts=None,
                      diamond_dir=None, is_managed=False, user_endpoint_config=None):
        endpoint = db.session.get(Endpoint, endpoint_uuid)
        if endpoint:
            endpoint.endpoint_name = endpoint_name
            endpoint.endpoint_host = endpoint_host
            endpoint.endpoint_status = endpoint_status
        else:
            endpoint = Endpoint(
                endpoint_uuid=endpoint_uuid,
                endpoint_name=endpoint_name,
                endpoint_host=endpoint_host,
                endpoint_status=endpoint_status,
                partitions=partitions or [],
                accounts=accounts or [],
                diamond_dir=diamond_dir or "",
                is_managed=is_managed,
                user_endpoint_config=user_endpoint_config,
            )
            db.session.add(endpoint)
        db.session.commit()

    def exists_endpoint(self, endpoint_uuid):
        return db.session.get(Endpoint, endpoint_uuid) is not None

    def update_endpoint_status(self, endpoint_uuid, endpoint_status):
        endpoint = db.session.get(Endpoint, endpoint_uuid)
        if endpoint:
            endpoint.endpoint_status = endpoint_status
            db.session.commit()

    def update_endpoint_managed_status(self, endpoint_uuid, is_managed):
        endpoint = db.session.get(Endpoint, endpoint_uuid)
        if endpoint:
            endpoint.is_managed = is_managed
            db.session.commit()

    def get_endpoints(self):
        return Endpoint.query.all()

    def get_managed_endpoints(self):
        return Endpoint.query.filter_by(is_managed=True).all()

    def get_endpoint_host(self, endpoint_uuid):
        endpoint = db.session.get(Endpoint, endpoint_uuid)
        return endpoint.endpoint_host if endpoint else None

    def get_diamond_dir(self, endpoint_uuid):
        endpoint = db.session.get(Endpoint, endpoint_uuid)
        return endpoint.diamond_dir if endpoint else ""

    def save_diamond_dir(self, endpoint_uuid, diamond_dir):
        endpoint = db.session.get(Endpoint, endpoint_uuid)
        if endpoint:
            endpoint.diamond_dir = diamond_dir
            db.session.commit()

    def get_endpoint_user_config(self, endpoint_uuid):
        endpoint = db.session.get(Endpoint, endpoint_uuid)
        return endpoint.user_endpoint_config if endpoint else None

    def update_endpoint_user_config(self, endpoint_uuid, user_endpoint_config):
        endpoint = db.session.get(Endpoint, endpoint_uuid)
        if endpoint:
            endpoint.user_endpoint_config = user_endpoint_config
            db.session.commit()

    def save_accounts(self, endpoint_uuid, accounts):
        endpoint = db.session.get(Endpoint, endpoint_uuid)
        if endpoint:
            endpoint.accounts = accounts
            db.session.commit()

    def get_accounts(self, endpoint_uuid):
        endpoint = db.session.get(Endpoint, endpoint_uuid)
        return endpoint.accounts if endpoint else []

    def save_partition(self, endpoint_uuid, partitions):
        endpoint = db.session.get(Endpoint, endpoint_uuid)
        if endpoint:
            endpoint.partitions = partitions
            db.session.commit()

    def get_partitions(self, endpoint_uuid):
        endpoint = db.session.get(Endpoint, endpoint_uuid)
        return endpoint.partitions if endpoint else []

    # ── Agent ─────────────────────────────────────────────────────────────────

    def save_agent(self, name, system_prompt, model="claude-sonnet-4-6"):
        agent = Agent(name=name, system_prompt=system_prompt, model=model)
        db.session.add(agent)
        db.session.commit()
        return agent

    def get_agent(self, agent_id):
        return db.session.get(Agent, agent_id)

    def list_agents(self):
        return Agent.query.order_by(Agent.created_at.desc()).all()

    def update_agent(self, agent_id, name=None, system_prompt=None, model=None):
        agent = db.session.get(Agent, agent_id)
        if not agent:
            return None
        if name is not None:
            agent.name = name
        if system_prompt is not None:
            agent.system_prompt = system_prompt
        if model is not None:
            agent.model = model
        db.session.commit()
        return agent

    def delete_agent(self, agent_id):
        agent = db.session.get(Agent, agent_id)
        if agent:
            db.session.delete(agent)
            db.session.commit()

    # ── AgentRun ──────────────────────────────────────────────────────────────

    def create_agent_run(self, agent_id, task, endpoint_id=None):
        run = AgentRun(agent_id=agent_id, task=task, endpoint_id=endpoint_id)
        db.session.add(run)
        db.session.commit()
        return run

    def get_agent_run(self, run_id):
        return db.session.get(AgentRun, run_id)

    def list_agent_runs(self, agent_id=None):
        q = AgentRun.query
        if agent_id:
            q = q.filter_by(agent_id=agent_id)
        return q.order_by(AgentRun.created_at.desc()).all()

    def update_agent_run(self, run_id, status=None, log=None, completed_at=None):
        run = db.session.get(AgentRun, run_id)
        if not run:
            return None
        if status is not None:
            run.status = status
        if log is not None:
            run.log = log
        if completed_at is not None:
            run.completed_at = completed_at
        db.session.commit()
        return run

    # ── Budget ────────────────────────────────────────────────────────────────

    def get_budget(self, endpoint_uuid=None):
        return NodeHourBudget.query.filter_by(endpoint_uuid=endpoint_uuid).first()

    def set_budget(self, max_node_hours, period="monthly", endpoint_uuid=None):
        budget = self.get_budget(endpoint_uuid)
        if budget:
            budget.max_node_hours = max_node_hours
            budget.period = period
        else:
            budget = NodeHourBudget(
                endpoint_uuid=endpoint_uuid,
                max_node_hours=max_node_hours,
                period=period,
            )
            db.session.add(budget)
        db.session.commit()
        return budget

    def delete_budget(self, endpoint_uuid=None):
        budget = self.get_budget(endpoint_uuid)
        if budget:
            db.session.delete(budget)
            db.session.commit()

    def get_usage_in_period(self, period="monthly", endpoint_uuid=None):
        q = db.session.query(func.coalesce(func.sum(NodeHourUsage.node_hours_estimated), 0.0)).filter(
            NodeHourUsage.recorded_at >= _period_start(period)
        )
        if endpoint_uuid:
            q = q.filter(NodeHourUsage.endpoint_uuid == endpoint_uuid)
        return q.scalar()

    def check_node_hour_budget(self, endpoint_uuid, nodes, walltime_secs):
        estimated = node_hours(nodes, walltime_secs)
        for ep_uuid in [endpoint_uuid, None]:
            budget = self.get_budget(endpoint_uuid=ep_uuid)
            if budget:
                used = self.get_usage_in_period(period=budget.period, endpoint_uuid=ep_uuid)
                remaining = budget.max_node_hours - used
                if estimated > remaining:
                    return False, remaining, budget
        return True, None, None

    def record_usage(self, task_id, endpoint_uuid, nodes, walltime_seconds_requested,
                     node_hours_estimated):
        usage = NodeHourUsage(
            task_id=task_id,
            endpoint_uuid=endpoint_uuid,
            nodes=nodes,
            walltime_seconds_requested=walltime_seconds_requested,
            node_hours_estimated=node_hours_estimated,
        )
        db.session.add(usage)
        db.session.commit()
        return usage

    def update_actual_usage(self, task_id, walltime_seconds_actual, node_hours_actual):
        usage = NodeHourUsage.query.filter_by(task_id=task_id).first()
        if usage:
            usage.walltime_seconds_actual = walltime_seconds_actual
            usage.node_hours_actual = node_hours_actual
            db.session.commit()

    def list_usage(self, period="monthly", endpoint_uuid=None, limit=200):
        q = NodeHourUsage.query.filter(NodeHourUsage.recorded_at >= _period_start(period))
        if endpoint_uuid:
            q = q.filter_by(endpoint_uuid=endpoint_uuid)
        return q.order_by(NodeHourUsage.recorded_at.desc()).limit(limit).all()
