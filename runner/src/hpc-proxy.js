/**
 * HPC API proxy — mounts on the HPC Agent HTTP server.
 *
 * All requests to /api/hpc/* are forwarded to the HPC backend (Python Flask).
 * This lets the monitor frontend reach the backend through the same origin,
 * avoiding CORS issues.
 *
 * Usage: call mountHpcProxy(server) after creating the HTTP server in server.js,
 * then handle /api/hpc/* requests by delegating to proxyHpcRequest().
 */

const HPC_BACKEND_URL = process.env.HPC_BACKEND_URL || 'http://localhost:5328';

/**
 * Given an HPC Agent HTTP request for /api/hpc/..., forward it to the HPC backend.
 * Returns a Response-like object { status, headers, body }.
 */
export async function proxyHpcRequest(req) {
  const url = req.url.replace(/^\/api\/hpc/, '/api');
  const targetUrl = `${HPC_BACKEND_URL}${url}`;

  const headers = {};
  if (req.headers['content-type']) {
    headers['content-type'] = req.headers['content-type'];
  }

  let body;
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    body = await readBody(req);
  }

  try {
    const res = await fetch(targetUrl, {
      method: req.method,
      headers,
      body,
    });
    const resBody = await res.text();
    return { status: res.status, contentType: res.headers.get('content-type') || 'application/json', body: resBody };
  } catch (err) {
    return {
      status: 502,
      contentType: 'application/json',
      body: JSON.stringify({ error: `HPC backend unreachable: ${err.message}` }),
    };
  }
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', chunk => chunks.push(chunk));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

/**
 * Returns true if the request URL is an HPC proxy request.
 */
export function isHpcRequest(url) {
  return url.startsWith('/api/hpc/') || url === '/api/hpc';
}
