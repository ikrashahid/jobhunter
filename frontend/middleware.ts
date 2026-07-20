import { NextRequest, NextResponse } from "next/server";

// Edge-safe HMAC — Web Crypto (middleware runs on Edge, not Node).
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
  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    encoder.encode("authenticated")
  );
  return Array.from(new Uint8Array(signature))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const cookie = req.cookies.get("jobhunter_auth")?.value;
  const expected = await expectedToken();
  const authed = Boolean(cookie && cookie === expected);

  if (pathname === "/login" || pathname.startsWith("/api/login")) {
    if (pathname === "/login" && authed) {
      return NextResponse.redirect(new URL("/", req.url));
    }
    return NextResponse.next();
  }

  if (!authed) {
    return NextResponse.redirect(new URL("/login", req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
