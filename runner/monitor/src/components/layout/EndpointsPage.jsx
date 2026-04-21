import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '../../utils/hpc-api.js';

function StatusBadge({ status }) {
  const color =
    status === 'online' ? 'bg-green-500' :
    status === 'offline' ? 'bg-red-500' :
    'bg-yellow-500';
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full text-white ${color}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-white/70" />
      {status || 'unknown'}
    </span>
  );
}

function EndpointCard({ endpoint, onToggleManaged, onSetWorkPath }) {
  const [expanding, setExpanding] = useState(false);
  const [workPath, setWorkPath] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function handleToggle() {
    setExpanding(true);
    try {
      await onToggleManaged(endpoint.endpoint_uuid, !endpoint.is_managed);
    } finally {
      setExpanding(false);
    }
  }

  async function handleSetPath(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await onSetWorkPath(endpoint.endpoint_uuid, workPath);
      setWorkPath('');
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-medium text-sm truncate">{endpoint.endpoint_name}</div>
          <div className="text-xs text-gray-400 truncate">{endpoint.endpoint_host}</div>
          <div className="text-xs text-gray-500 font-mono mt-0.5 truncate">{endpoint.endpoint_uuid}</div>
        </div>
        <div className="flex flex-col items-end gap-2 shrink-0">
          <StatusBadge status={endpoint.endpoint_status} />
          <button
            onClick={handleToggle}
            disabled={expanding}
            className={`text-xs px-3 py-1 rounded font-medium transition-colors ${
              endpoint.is_managed
                ? 'bg-blue-600/30 text-blue-300 hover:bg-blue-600/50'
                : 'bg-white/10 text-gray-300 hover:bg-white/20'
            }`}
          >
            {expanding ? '...' : endpoint.is_managed ? 'Managed' : 'Add'}
          </button>
        </div>
      </div>

      {endpoint.is_managed && (
        <div className="space-y-2">
          {endpoint.diamond_dir && (
            <div className="text-xs text-gray-400">
              Work dir: <span className="font-mono text-gray-300">{endpoint.diamond_dir}</span>
            </div>
          )}

          {endpoint.partitions?.length > 0 && (
            <div className="text-xs text-gray-400">
              Partitions: {endpoint.partitions.map(p => (
                <span key={p} className="ml-1 px-1.5 py-0.5 rounded bg-white/10 font-mono">{p}</span>
              ))}
            </div>
          )}

          {endpoint.accounts?.length > 0 && (
            <div className="text-xs text-gray-400">
              Accounts: {endpoint.accounts.map(a => (
                <span key={a} className="ml-1 px-1.5 py-0.5 rounded bg-white/10 font-mono">{a}</span>
              ))}
            </div>
          )}

          {!endpoint.diamond_dir && (
            <form onSubmit={handleSetPath} className="flex gap-2">
              <input
                type="text"
                value={workPath}
                onChange={e => setWorkPath(e.target.value)}
                placeholder="/path/to/work/dir"
                className="flex-1 text-xs bg-black/30 border border-white/20 rounded px-2 py-1 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
              <button
                type="submit"
                disabled={saving || !workPath}
                className="text-xs px-3 py-1 rounded bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium"
              >
                {saving ? '...' : 'Set path'}
              </button>
            </form>
          )}
          {error && <div className="text-xs text-red-400">{error}</div>}
        </div>
      )}
    </div>
  );
}

export default function EndpointsPage() {
  const [endpoints, setEndpoints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingPartitions, setLoadingPartitions] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const data = await apiFetch('/list_all_endpoints');
      setEndpoints(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleRefresh() {
    setRefreshing(true);
    setError('');
    try {
      await apiFetch('/register_all_endpoints', { method: 'POST' });
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setRefreshing(false);
    }
  }

  async function handleToggleManaged(endpoint_uuid, is_managed) {
    await apiFetch(`/manage_endpoint/${endpoint_uuid}`, {
      method: 'PUT',
      body: JSON.stringify({ is_managed }),
    });
    if (is_managed) {
      // Load accounts and partitions for newly managed endpoint
      setLoadingPartitions(endpoint_uuid);
      try {
        await apiFetch('/load_accounts_partitions', {
          method: 'POST',
          body: JSON.stringify({ endpoint_uuid }),
        });
      } catch {
        // non-fatal
      } finally {
        setLoadingPartitions('');
      }
    }
    await load();
  }

  async function handleSetWorkPath(endpoint_uuid, work_path) {
    await apiFetch('/set_work_path', {
      method: 'POST',
      body: JSON.stringify({ endpoint_uuid, work_path }),
    });
    await load();
  }

  const managed = endpoints.filter(e => e.is_managed);
  const available = endpoints.filter(e => !e.is_managed);

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Endpoints</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Manage HPC machines connected via Globus Compute
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="text-sm px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium"
        >
          {refreshing ? 'Refreshing...' : 'Refresh Endpoints'}
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {loadingPartitions && (
        <div className="text-sm text-blue-400">Loading accounts & partitions for new endpoint...</div>
      )}

      {loading ? (
        <div className="text-sm text-gray-400">Loading...</div>
      ) : (
        <>
          {managed.length > 0 && (
            <section>
              <h2 className="text-sm font-medium text-gray-300 mb-3">
                Managed ({managed.length})
              </h2>
              <div className="grid gap-3 sm:grid-cols-2">
                {managed.map(ep => (
                  <EndpointCard
                    key={ep.endpoint_uuid}
                    endpoint={ep}
                    onToggleManaged={handleToggleManaged}
                    onSetWorkPath={handleSetWorkPath}
                  />
                ))}
              </div>
            </section>
          )}

          {available.length > 0 && (
            <section>
              <h2 className="text-sm font-medium text-gray-400 mb-3">
                Available ({available.length})
              </h2>
              <div className="grid gap-3 sm:grid-cols-2">
                {available.map(ep => (
                  <EndpointCard
                    key={ep.endpoint_uuid}
                    endpoint={ep}
                    onToggleManaged={handleToggleManaged}
                    onSetWorkPath={handleSetWorkPath}
                  />
                ))}
              </div>
            </section>
          )}

          {endpoints.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              <div className="text-lg mb-2">No endpoints found</div>
              <div className="text-sm">Click "Refresh Endpoints" to discover your Globus Compute endpoints</div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
