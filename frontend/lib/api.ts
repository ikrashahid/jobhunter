/**
 * Browser-facing API client.
 *
 * All calls go same-origin to /api/* — Next.js proxies them to the FastAPI
 * backend with the shared secret. The Railway URL and API_KEY never ship
 * to the browser (no NEXT_PUBLIC_ backend vars).
 */

async function readError(res: Response, path: string, method: string): Promise<never> {
  let detail = "";
  try {
    const data = await res.json();
    detail = data.error || data.detail || JSON.stringify(data);
  } catch {
    try {
      detail = (await res.text()).slice(0, 200);
    } catch {
      detail = "";
    }
  }
  throw new Error(
    detail
      ? `${method} ${path} failed: ${res.status} — ${detail}`
      : `${method} ${path} failed: ${res.status}`
  );
}

async function get(path: string) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) return readError(res, path, "GET");
  return res.json();
}

async function post(path: string, body: unknown) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) return readError(res, path, "POST");
  return res.json();
}

async function patch(path: string, body: unknown) {
  const res = await fetch(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) return readError(res, path, "PATCH");
  return res.json();
}

export const api = { get, post, patch };
