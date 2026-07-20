import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";

// The cookie value is a signed token, not the raw password — so even
// if someone inspects cookies in devtools, they can't reuse the value
// to forge a session without knowing AUTH_SECRET too.
function makeToken(): string {
  const secret = process.env.AUTH_SECRET || "";
  return crypto.createHmac("sha256", secret).update("authenticated").digest("hex");
}

export async function POST(req: NextRequest) {
  const { username, password } = await req.json();

  const validUsername = process.env.AUTH_USERNAME;
  const validPassword = process.env.AUTH_PASSWORD;

  if (!validUsername || !validPassword || !process.env.AUTH_SECRET) {
    return NextResponse.json(
      { error: "Auth not configured on the server" },
      { status: 500 }
    );
  }

  // Timing-safe comparison so response time doesn't leak how much of
  // the password was guessed correctly.
  const usernameOk =
    username?.length === validUsername.length &&
    crypto.timingSafeEqual(Buffer.from(username), Buffer.from(validUsername));
  const passwordOk =
    password?.length === validPassword.length &&
    crypto.timingSafeEqual(Buffer.from(password), Buffer.from(validPassword));

  if (!usernameOk || !passwordOk) {
    return NextResponse.json({ error: "Invalid credentials" }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set("jobhunter_auth", makeToken(), {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30, // 30 days
    path: "/",
  });

  return response;
}