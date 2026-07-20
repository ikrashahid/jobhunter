import { NextRequest, NextResponse } from "next/server";

// Node's `crypto` module doesn't work in Next.js middleware (it runs on
// the Edge Runtime, not Node.js) — this uses the Web Crypto API instead,
// which is Edge-compatible. The login API route (app/api/login/route.ts)
// still uses Node's crypto, since API routes run on Node.js by default —
// only middleware needs this Edge-safe version.
async function expectedToken(): Promise<string> {
  const secret = process.env.AUTH_SECRET || "";
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode("authenticated"));
  return Array.from(new Uint8Array(signature))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Let the login page itself and its API route through — otherwise
  // nobody could ever reach the login form to begin with.
  if (pathname === "/login" || pathname.startsWith("/api/login")) {
    return NextResponse.next();
  }

  const cookie = req.cookies.get("jobhunter_auth")?.value;
  const expected = await expectedToken();

  if (!cookie || cookie !== expected) {
    const loginUrl = new URL("/login", req.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

// Protects every route except Next.js internals and static files.
export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};