import { NextRequest, NextResponse } from "next/server";

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
]);

function backendConfig() {
  const base = (process.env.BACKEND_URL || "").replace(/\/$/, "");
  const apiKey = process.env.API_KEY || "";
  if (!base) {
    return { error: NextResponse.json({ error: "BACKEND_URL is not configured" }, { status: 500 }) };
  }
  if (!apiKey) {
    return { error: NextResponse.json({ error: "API_KEY is not configured" }, { status: 500 }) };
  }
  return { base, apiKey };
}

async function forward(
  req: NextRequest,
  pathParts: string[]
): Promise<NextResponse> {
  const cfg = backendConfig();
  if ("error" in cfg && cfg.error) return cfg.error;

  const { base, apiKey } = cfg as { base: string; apiKey: string };
  const subpath = pathParts.join("/");
  const target = new URL(`${base}/api/${subpath}`);
  target.search = req.nextUrl.search;

  const headers = new Headers();
  headers.set("X-API-Key", apiKey);

  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);

  const init: RequestInit = {
    method: req.method,
    headers,
    cache: "no-store",
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, init);
  } catch (err) {
    const message = err instanceof Error ? err.message : "upstream unreachable";
    return NextResponse.json({ error: `Backend unreachable: ${message}` }, { status: 502 });
  }

  const outHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      outHeaders.set(key, value);
    }
  });

  // Stream body through — works for JSON and PDF downloads alike.
  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: outHeaders,
  });
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return forward(req, path);
}

export async function POST(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return forward(req, path);
}

export async function PATCH(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return forward(req, path);
}

export async function PUT(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return forward(req, path);
}

export async function DELETE(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return forward(req, path);
}
