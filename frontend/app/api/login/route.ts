import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";

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

  const usernameOk =
    typeof username === "string" &&
    username.length === validUsername.length &&
    crypto.timingSafeEqual(Buffer.from(username), Buffer.from(validUsername));
  const passwordOk =
    typeof password === "string" &&
    password.length === validPassword.length &&
    crypto.timingSafeEqual(Buffer.from(password), Buffer.from(validPassword));

  if (!usernameOk || !passwordOk) {
    return NextResponse.json({ error: "Invalid credentials" }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set("jobhunter_auth", makeToken(), {
    httpOnly: true,
    // localhost is http — secure cookies would never stick in dev
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30,
    path: "/",
  });

  return response;
}
