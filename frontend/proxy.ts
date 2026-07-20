import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";

function expectedToken(): string {
  const secret = process.env.AUTH_SECRET || "";
  return crypto.createHmac("sha256", secret).update("authenticated").digest("hex");
}

export async function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const cookie = req.cookies.get("jobhunter_auth")?.value;
  const expected = expectedToken();
  const authed = Boolean(cookie && cookie === expected);

  // Public auth endpoints — and nothing else.
  if (pathname === "/login" || pathname.startsWith("/api/login")) {
    if (pathname === "/login" && authed) {
      return NextResponse.redirect(new URL("/", req.url));
    }
    return NextResponse.next();
  }

  if (!authed) {
    // Don't redirect API callers to HTML login — return JSON 401.
    if (pathname.startsWith("/api/")) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.redirect(new URL("/login", req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
