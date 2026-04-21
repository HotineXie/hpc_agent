const HPC_API = '/api/hpc';

export async function apiFetch(path, opts = {}) {
  const res = await fetch(`${HPC_API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}
