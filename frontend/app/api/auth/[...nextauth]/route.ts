/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
