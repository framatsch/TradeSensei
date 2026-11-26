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

import { Suspense } from "react";
import { LoginForm } from "@/components/auth/LoginForm";
import { OAuthErrorBanner } from "@/components/auth/OAuthErrorBanner";
import { PasswordResetSuccessBanner } from "@/components/auth/PasswordResetSuccessBanner";
import { LoginHeader } from "@/components/auth/LoginHeader";

export const metadata = {
  title: "Sign In — Trade Sensei",
};

export default function LoginPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-lg items-center p-4">
      <section className="solid-card w-full space-y-4 p-6">
        <LoginHeader />

        {/* Password reset success notice */}
        <Suspense>
          <PasswordResetSuccessBanner />
        </Suspense>

        {/* OAuth error banner — shown when redirected back from a failed OAuth flow */}
        <Suspense>
          <OAuthErrorBanner />
        </Suspense>

        <LoginForm />
      </section>
    </main>
  );
}
