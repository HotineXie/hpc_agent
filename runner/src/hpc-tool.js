const HPC_BACKEND_URL = process.env.HPC_BACKEND_URL || 'http://localhost:5328';
const POLL_INTERVAL_MS = parseInt(process.env.HPC_POLL_INTERVAL_MS || '30000', 10);
const POLL_MAX_ATTEMPTS = parseInt(process.env.HPC_POLL_MAX_ATTEMPTS || '720', 10); // 6h default

/**
 * @param {Object} defaults - Project-level HPC defaults (endpoint_id, account, available_partitions)
 */
export function getHpcToolDefinition(defaults = {}) {
  const partitionHint = defaults.available_partitions?.length
    ? ` Available on this endpoint: ${defaults.available_partitions.join(', ')}.`
    : '';
  const accountHint = defaults.account
    ? ` Defaults to "${defaults.account}" if omitted.`
    : '';

  return {
    name: 'HpcSubmit',
    description:
      'Submit a SLURM job to the project\'s HPC cluster and wait for it to complete. ' +
      'Returns the job stdout log when the job finishes. ' +
      'The agent is paused while waiting — no tokens are consumed during the wait. ' +
      'Prefer structured params (command, nodes, walltime, partition) over raw_script.',
    input_schema: {
      type: 'object',
      properties: {
        task_name: {
          type: 'string',
          description: 'Short alphanumeric name for the SLURM job (no spaces).',
        },
        command: {
          type: 'string',
          description:
            'Shell command(s) to execute on the HPC node (e.g. "python train.py --epochs 100"). ' +
            'Use this for most jobs instead of writing a raw sbatch script.',
        },
        partition: {
          type: 'string',
          description: `SLURM partition to submit to.${partitionHint}`,
        },
        nodes: {
          type: 'number',
          description: 'Number of compute nodes to request.',
        },
        walltime: {
          type: 'string',
          description: 'Maximum job duration in HH:MM:SS format (e.g. "2:00:00").',
        },
        account: {
          type: 'string',
          description: `SLURM account/allocation to charge.${accountHint}`,
        },
        endpoint_id: {
          type: 'string',
          description: "Globus Compute endpoint UUID. Defaults to the project's configured HPC endpoint.",
        },
        raw_script: {
          type: 'string',
          description:
            'Complete sbatch script (#!/bin/bash + #SBATCH directives + commands). ' +
            'Use only when you need full SLURM control; prefer command + structured params.',
        },
        agent_run_id: {
          type: 'string',
          description: 'Agent run ID to associate this HPC task with (auto-provided).',
        },
      },
      required: ['task_name'],
    },
  };
}

function parseWalltimeSeconds(walltime) {
  const m = String(walltime || '').match(/^(\d+):(\d{2}):(\d{2})$/);
  if (!m) return 3600;
  return parseInt(m[1]) * 3600 + parseInt(m[2]) * 60 + parseInt(m[3]);
}

// Extract nodes and walltime from #SBATCH headers in a raw script for budget tracking.
function parseScriptBudgetParams(raw_script) {
  let nodes = 1;
  let walltimeStr = '1:00:00';
  for (const line of (raw_script || '').split('\n')) {
    if (!line.startsWith('#SBATCH')) continue;
    const nm = line.match(/--nodes[=\s]+(\d+)/);
    if (nm) nodes = parseInt(nm[1]);
    const tm = line.match(/--time[=\s]+(\d+:\d{2}:\d{2})/);
    if (tm) walltimeStr = tm[1];
  }
  return { nodes, walltime_seconds: parseWalltimeSeconds(walltimeStr) };
}

async function hpcFetch(path, opts = {}) {
  const res = await fetch(`${HPC_BACKEND_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  });
  const body = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, body };
}

async function checkBudget(endpoint_id, nodes, walltime_seconds) {
  const { ok, body } = await hpcFetch('/api/budget/check', {
    method: 'POST',
    body: JSON.stringify({ endpoint_id, nodes, walltime_seconds }),
  });
  if (!ok) throw new Error(`Budget check failed: ${JSON.stringify(body)}`);
  return body; // { allowed, estimated_node_hours, remaining_node_hours?, period }
}

async function submitJob(params) {
  const { ok, status, body } = await hpcFetch('/api/submit_task', {
    method: 'POST',
    body: JSON.stringify(params),
  });
  if (!ok) throw new Error(`Job submission failed (${status}): ${JSON.stringify(body)}`);
  return body; // { task_id, batch_job_id, task_name, stdout_path }
}

async function pollJobStatus(task_id) {
  const { ok, body } = await hpcFetch('/api/get_task_status');
  if (!ok) throw new Error('Failed to poll task status');
  const tasks = Array.isArray(body) ? body : [];
  return tasks.find((t) => t.task_id === task_id) || null;
}

async function fetchJobLog(task_id) {
  const { ok, body } = await hpcFetch(`/api/get_task_log?task_id=${task_id}`);
  if (!ok) return `Failed to fetch log: ${JSON.stringify(body)}`;
  return body.content || '';
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * @param {Object} input   - Tool input from the agent
 * @param {Object} defaults - Project-level HPC defaults from config.yaml hpc section
 */
export async function executeHpcSubmit(input, defaults = {}) {
  const {
    endpoint_id: inputEndpointId,
    task_name,
    command,
    nodes: inputNodes,
    walltime: inputWalltime,
    partition: inputPartition,
    account: inputAccount,
    raw_script,
    agent_run_id,
  } = input;

  const endpoint_id = inputEndpointId || defaults.endpoint_id;
  const nodes = inputNodes ?? 1;
  const walltime = inputWalltime || '1:00:00';
  const partition = inputPartition;
  const account = inputAccount || defaults.account;

  if (!endpoint_id) {
    return (
      '[HpcSubmit Error] No HPC endpoint configured. ' +
      'Set hpc.endpoint_uuid in project config.yaml or pass endpoint_id explicitly.'
    );
  }

  if (!raw_script && !command) {
    return '[HpcSubmit Error] Provide either command (preferred) or raw_script.';
  }

  // Derive budget params — parse from script headers when raw_script is used.
  const budgetParams = raw_script
    ? parseScriptBudgetParams(raw_script)
    : { nodes, walltime_seconds: parseWalltimeSeconds(walltime) };

  // 1. Budget check
  let budgetResult;
  try {
    budgetResult = await checkBudget(endpoint_id, budgetParams.nodes, budgetParams.walltime_seconds);
  } catch (err) {
    return `[HpcSubmit Error] Budget check failed: ${err.message}`;
  }
  if (!budgetResult.allowed) {
    return (
      `[HpcSubmit Blocked] Node-hour budget exceeded.\n` +
      `Estimated: ${budgetResult.estimated_node_hours} node-hours\n` +
      `Remaining: ${budgetResult.remaining_node_hours} node-hours (${budgetResult.period} budget)\n` +
      `Please reduce the job size or contact the administrator to increase the budget.`
    );
  }

  // 2. Submit — raw_script bypasses the template; structured params use the Jinja2 template.
  const submitParams = raw_script
    ? { endpoint_id, task_name, raw_script, agent_run_id }
    : {
        endpoint_id,
        task_name,
        task_command: command || '',
        partition,
        account,
        time_duration: walltime,
        num_of_nodes: nodes,
        agent_run_id,
      };

  let submission;
  try {
    submission = await submitJob(submitParams);
  } catch (err) {
    return `[HpcSubmit Error] Submission failed: ${err.message}`;
  }

  const { task_id, batch_job_id } = submission;
  process.stderr.write(
    `[HpcSubmit] Job submitted. task_id=${task_id} slurm_job=${batch_job_id}. ` +
    `Polling every ${POLL_INTERVAL_MS / 1000}s...\n`
  );

  // 3. Poll until terminal state — agent sleeps here, no tokens consumed
  const TERMINAL = new Set(['COMPLETED', 'FAILED', 'MISSING']);
  for (let attempt = 0; attempt < POLL_MAX_ATTEMPTS; attempt++) {
    await sleep(POLL_INTERVAL_MS);

    let taskInfo;
    try {
      taskInfo = await pollJobStatus(task_id);
    } catch (err) {
      process.stderr.write(`[HpcSubmit] Poll error (will retry): ${err.message}\n`);
      continue;
    }

    const status = taskInfo?.task_status;
    process.stderr.write(`[HpcSubmit] Poll ${attempt + 1}: status=${status || 'unknown'}\n`);

    if (status && TERMINAL.has(status)) {
      // 4. Fetch log
      let log = '';
      try {
        log = await fetchJobLog(task_id);
      } catch (err) {
        log = `Failed to fetch log: ${err.message}`;
      }

      return (
        `[HpcSubmit] Job ${status}.\n` +
        `  task_id:      ${task_id}\n` +
        `  slurm_job_id: ${batch_job_id}\n` +
        `  status:       ${status}\n\n` +
        `=== JOB OUTPUT ===\n${log}\n=== END OUTPUT ===`
      );
    }
  }

  return (
    `[HpcSubmit] Timed out waiting for job ${task_id} (${batch_job_id}) after ` +
    `${(POLL_MAX_ATTEMPTS * POLL_INTERVAL_MS) / 3600000}h. Check status manually.`
  );
}
