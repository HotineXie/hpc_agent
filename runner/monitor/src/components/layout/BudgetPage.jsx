import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '../../utils/hpc-api.js';

function UsageBar({ used, max }) {
  const pct = max > 0 ? Math.min(100, (used / max) * 100) : 0;
  const color = pct > 90 ? 'bg-red-500' : pct > 70 ? 'bg-yellow-500' : 'bg-blue-500';
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-400">
        <span>{used.toFixed(2)} node-hours used</span>
        <span>{max.toFixed(2)} max</span>
      </div>
      <div className="h-2 rounded-full bg-white/10 overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="text-xs text-gray-500 text-right">
        {(max - used).toFixed(2)} remaining ({pct.toFixed(1)}% used)
      </div>
    </div>
  );
}

function BudgetForm({ endpointUuid, initialBudget, onSaved }) {
  const [maxHours, setMaxHours] = useState(initialBudget?.max_node_hours?.toString() || '');
  const [period, setPeriod] = useState(initialBudget?.period || 'monthly');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    const val = parseFloat(maxHours);
    if (!val || val <= 0) {
      setError('Enter a positive number');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await apiFetch('/budget', {
        method: 'POST',
        body: JSON.stringify({
          max_node_hours: val,
          period,
          endpoint_uuid: endpointUuid || null,
        }),
      });
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex gap-3 items-end">
        <div className="flex-1 space-y-1">
          <label className="text-xs text-gray-400">Max node-hours</label>
          <input
            type="number"
            min="0"
            step="any"
            value={maxHours}
            onChange={e => setMaxHours(e.target.value)}
            placeholder="e.g. 100"
            className="w-full text-sm bg-black/30 border border-white/20 rounded px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
        </div>
        <div className="w-36 space-y-1">
          <label className="text-xs text-gray-400">Period</label>
          <select
            value={period}
            onChange={e => setPeriod(e.target.value)}
            className="w-full text-sm bg-black/30 border border-white/20 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
        <button
          type="submit"
          disabled={saving}
          className="text-sm px-4 py-2 rounded bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium"
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>
      {error && <div className="text-xs text-red-400">{error}</div>}
    </form>
  );
}

function BudgetCard({ label, budget, endpointUuid, onRefresh }) {
  const [editing, setEditing] = useState(!budget);
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    setDeleting(true);
    try {
      const url = endpointUuid
        ? `/budget?endpoint_uuid=${endpointUuid}`
        : '/budget';
      await apiFetch(url, { method: 'DELETE' });
      onRefresh();
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-medium text-sm">{label}</div>
          {budget && (
            <div className="text-xs text-gray-400 mt-0.5">
              {budget.period.charAt(0).toUpperCase() + budget.period.slice(1)} budget
            </div>
          )}
        </div>
        <div className="flex gap-2">
          {budget && (
            <>
              <button
                onClick={() => setEditing(!editing)}
                className="text-xs px-3 py-1 rounded bg-white/10 hover:bg-white/20 text-gray-300"
              >
                {editing ? 'Cancel' : 'Edit'}
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="text-xs px-3 py-1 rounded bg-red-500/20 hover:bg-red-500/30 text-red-400"
              >
                Remove
              </button>
            </>
          )}
        </div>
      </div>

      {budget && !editing && (
        <UsageBar used={budget.used_node_hours} max={budget.max_node_hours} />
      )}

      {(!budget || editing) && (
        <BudgetForm
          endpointUuid={endpointUuid}
          initialBudget={budget}
          onSaved={() => { setEditing(false); onRefresh(); }}
        />
      )}
    </div>
  );
}

function UsageTable({ period, endpointUuid }) {
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const url = `/budget/usage?period=${period}` + (endpointUuid ? `&endpoint_uuid=${endpointUuid}` : '');
    apiFetch(url)
      .then(setUsage)
      .catch(() => setUsage(null))
      .finally(() => setLoading(false));
  }, [period, endpointUuid]);

  if (loading) return <div className="text-xs text-gray-500">Loading usage...</div>;
  if (!usage) return null;

  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-400">
        {period} usage: <span className="text-white font-medium">{usage.total_estimated_node_hours.toFixed(2)}</span> node-hours estimated
        {usage.total_actual_node_hours > 0 && `, ${usage.total_actual_node_hours.toFixed(2)} actual`}
      </div>
      {usage.records.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500 border-b border-white/10">
                <th className="text-left py-1 pr-3">Job</th>
                <th className="text-right py-1 pr-3">Nodes</th>
                <th className="text-right py-1 pr-3">Walltime</th>
                <th className="text-right py-1 pr-3">Est. node-h</th>
                <th className="text-right py-1">Recorded</th>
              </tr>
            </thead>
            <tbody>
              {usage.records.slice(0, 50).map((r, i) => (
                <tr key={i} className="border-b border-white/5 text-gray-300">
                  <td className="py-1 pr-3 font-mono truncate max-w-32">{r.task_id?.slice(0, 8)}…</td>
                  <td className="py-1 pr-3 text-right">{r.nodes}</td>
                  <td className="py-1 pr-3 text-right">{Math.round(r.walltime_seconds_requested / 60)}m</td>
                  <td className="py-1 pr-3 text-right">{r.node_hours_estimated.toFixed(2)}</td>
                  <td className="py-1 text-right text-gray-500">{r.recorded_at?.slice(0, 16)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function BudgetPage() {
  const [globalBudget, setGlobalBudget] = useState(undefined);
  const [endpointBudgets, setEndpointBudgets] = useState([]);
  const [endpoints, setEndpoints] = useState([]);
  const [selectedPeriod, setSelectedPeriod] = useState('monthly');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [budgetData, epData] = await Promise.all([
        apiFetch('/budget'),
        apiFetch('/list_all_endpoints').catch(() => []),
      ]);
      setGlobalBudget(budgetData.budget);

      // Load per-endpoint budgets for managed endpoints
      const managed = Array.isArray(epData) ? epData.filter(e => e.is_managed) : [];
      setEndpoints(managed);

      const epBudgets = await Promise.all(
        managed.map(ep =>
          apiFetch(`/budget?endpoint_uuid=${ep.endpoint_uuid}`)
            .then(d => ({ endpoint: ep, budget: d.budget }))
            .catch(() => ({ endpoint: ep, budget: null }))
        )
      );
      setEndpointBudgets(epBudgets.filter(b => b.budget !== undefined));
    } catch {
      // non-fatal
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return <div className="p-6 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-xl font-semibold">Node-Hour Budget</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          Limit how many node-hours agents can consume across HPC jobs
        </p>
      </div>

      <section className="space-y-4">
        <h2 className="text-sm font-medium text-gray-300">Global Budget</h2>
        <p className="text-xs text-gray-500">
          Applies to all endpoints. Per-endpoint budgets (below) further restrict individual machines.
        </p>
        <BudgetCard
          label="Global"
          budget={globalBudget}
          endpointUuid={null}
          onRefresh={load}
        />
        {globalBudget && (
          <UsageTable period={globalBudget.period} endpointUuid={null} />
        )}
      </section>

      {endpoints.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-sm font-medium text-gray-300">Per-Endpoint Budgets</h2>
          {endpointBudgets.map(({ endpoint, budget }) => (
            <div key={endpoint.endpoint_uuid}>
              <BudgetCard
                label={endpoint.endpoint_name}
                budget={budget}
                endpointUuid={endpoint.endpoint_uuid}
                onRefresh={load}
              />
              {budget && <UsageTable period={budget.period} endpointUuid={endpoint.endpoint_uuid} />}
            </div>
          ))}
        </section>
      )}

      <section className="space-y-3">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-medium text-gray-300">Usage History</h2>
          <select
            value={selectedPeriod}
            onChange={e => setSelectedPeriod(e.target.value)}
            className="text-xs bg-black/30 border border-white/20 rounded px-2 py-1 text-white"
          >
            <option value="daily">Last 24h</option>
            <option value="weekly">Last 7 days</option>
            <option value="monthly">Last 30 days</option>
          </select>
        </div>
        <UsageTable period={selectedPeriod} endpointUuid={null} />
      </section>
    </div>
  );
}
