# Remote functions for Globus Compute — all imports are inside each function
# so they are self-contained when deserialized and exec'd on the endpoint.


def get_machine_metadata():
    import getpass
    import os
    import shutil
    import subprocess
    import sys

    def _env():
        env = os.environ.copy()
        if not env.get("USER"):
            try:
                env["USER"] = getpass.getuser()
            except Exception:
                pass
        return env

    def run(cmd):
        try:
            result = subprocess.run(
                cmd, shell=isinstance(cmd, str), check=False,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=_env(),
            )
            return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "returncode": result.returncode}
        except Exception as exc:
            return {"stdout": "", "stderr": str(exc), "returncode": -1}

    batch_system = None
    partitions = []
    partition_error = None

    if shutil.which("sinfo"):
        batch_system = "slurm"
        r = run('sinfo -h -o "%P"')
        if r["returncode"] == 0:
            seen = set()
            for line in r["stdout"].splitlines():
                p = line.strip().rstrip("*")
                if p and p not in seen:
                    seen.add(p)
                    partitions.append(p)
        else:
            partition_error = r["stderr"] or r["stdout"]
    elif shutil.which("qstat"):
        batch_system = "pbs"
    elif shutil.which("bqueues"):
        batch_system = "lsf"
    else:
        batch_system = "unknown"

    accounts = []
    accounts_error = None

    if shutil.which("sacctmgr"):
        user = os.environ.get("USER", "") or getpass.getuser()
        for cmd in [
            f"sacctmgr show associations --noheader -P user={user} format=Account",
            f"sacctmgr -n -p show associations user={user} format=Account",
            f"sacctmgr -n -p show associations where user={user} format=Account",
        ]:
            r = run(cmd)
            if r["returncode"] == 0 and r["stdout"]:
                accounts = [x.strip() for x in r["stdout"].splitlines() if x.strip()]
                accounts_error = None
                break
            accounts_error = r["stderr"] or r["stdout"] or f"exit {r['returncode']}"
    else:
        accounts_error = "sacctmgr not available"

    return {
        "batch_system": batch_system,
        "partitions": partitions,
        "partition_error": partition_error,
        "accounts": accounts,
        "accounts_error": accounts_error,
        "home_directory": os.path.expanduser("~"),
        "python": {"executable": sys.executable, "version": sys.version},
    }


def fetch_task_status(batch_job_id):
    import subprocess
    result = subprocess.run(
        ["bash", "-c", f"sacct -j {batch_job_id} -o State -n | head -n 1"],
        capture_output=True, text=True,
    )
    return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "returncode": result.returncode}


def check_diamond_work_path(diamond_work_path):
    import os
    if os.path.isdir(diamond_work_path) and os.access(diamond_work_path, os.W_OK):
        return "1"
    return "0"


def create_diamond_dir(diamond_dir, diamond_log_dir):
    import os
    os.makedirs(diamond_dir, exist_ok=True)
    os.makedirs(diamond_log_dir, exist_ok=True)
    return {"status": "ok"}


def run_submit_script(submit_script):
    import subprocess
    result = subprocess.run(
        ["bash", "-c", submit_script],
        capture_output=True, text=True,
    )
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


def get_task_log(log_file_path, eof_flag="EOF"):
    import os
    abs_log_path = os.path.expanduser(os.path.expandvars(log_file_path))
    try:
        with open(abs_log_path, "r") as f:
            content = f.read()
            is_complete = content.rstrip().endswith(eof_flag)
            return {"content": content, "is_complete": is_complete}
    except Exception as exc:
        return {"content": f"Error reading log file: {str(exc)}", "is_complete": False, "error": str(exc)}
