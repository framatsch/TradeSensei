/**
 * NextAuth.js route handler.
 *
 * NOTE: The backend owns the full Google OAuth Authorization Code Flow.
 * This handler is present for compatibility but Google sign-in is initiated
 * by redirecting the browser directly to `GET /api/v1/auth/google` on the
 * backend — not through NextAuth's Google provider.
 *
 * If additional OAuth providers are added in the future, configure them here
 * and update `GoogleSignInButton` to call `signIn("<provider>")`.
 */

import NextAuth from "next-auth";
import type { NextAuthOptions } from "next-auth";

const authOptions: NextAuthOptions = {
  providers: [],
  // No session is persisted — the backend JWT stored in localStorage is the
  // source of truth for auth state.
  session: { strategy: "jwt" },
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
