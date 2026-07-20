/**
 * Browser-facing API client.
 *
 * All calls go same-origin to /api/* — Next.js proxies them to the FastAPI
 * backend with the shared secret. The Railway URL and API_KEY never ship
 * to the browser (no NEXT_PUBLIC_ backend vars).
 */

async function get(path: string) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function post(path: string, body: unknown) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}

async function patch(path: string, body: unknown) {
  const res = await fetch(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`PATCH ${path} failed: ${res.status}`);
  return res.json();
}

export const api = { get, post, patch };
