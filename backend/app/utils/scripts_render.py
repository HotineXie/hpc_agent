import os
import re
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")

env = Environment(loader=FileSystemLoader(_TEMPLATES_DIR))
task_templates_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    undefined=StrictUndefined,
)

TASK_TEMPLATE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def render_submit_task_script(
    task_name, location, stdout_path, stderr_path,
    time_duration, partition, account, reservation,
    num_of_nodes, task_command, slurm_options="",
):
    tpl = env.get_template("submit_task.j2")
    return tpl.render(
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


def render_task_template_script(template_name: str, context: dict[str, Any]):
    if not template_name or not TASK_TEMPLATE_NAME_PATTERN.fullmatch(template_name):
        raise ValueError("Invalid task template name")
    tpl = task_templates_env.get_template(template_name)
    return tpl.render(**context)
