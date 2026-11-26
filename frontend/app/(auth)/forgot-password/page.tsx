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

"use client";

import { useState } from "react";
import Link from "next/link";
import { Logo } from "@/components/ui/Logo";
import { Spinner } from "@/components/ui/Spinner";
import { forgotPasswordApiV1AuthForgotPasswordPost } from "@/lib/api/index";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await forgotPasswordApiV1AuthForgotPasswordPost({ body: { email } });
    } catch {
      // Intentionally ignore errors — always show the success message
      // to prevent user enumeration.
    } finally {
      setIsLoading(false);
      setSubmitted(true);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-lg items-center p-4">
      <section className="solid-card w-full space-y-4 p-6">
        <div className="flex flex-col items-center gap-3 text-center">
          <Logo size={72} className="rounded-2xl" />
          <h1 className="text-2xl font-semibold text-foreground">
            Reset your password
          </h1>
        </div>

        {submitted ? (
          <div className="space-y-4 text-center">
            <p className="text-foreground text-sm">
              If an account with that email exists, we&apos;ve sent a reset
              link. Check your inbox — the link is valid for 1 hour.
            </p>
            <p className="text-xs text-muted-foreground">
              Didn&apos;t receive it? Check your spam folder.
            </p>
            <Link
              href="/login"
              className="block mt-4 text-sm text-primary hover:text-primary/80 font-medium transition-colors"
            >
              Back to sign in
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Enter your email address and we&apos;ll send you a link to reset
              your password.
            </p>

            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-muted-foreground mb-1"
              >
                Email address
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 bg-secondary border border-border rounded-md text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                placeholder="you@example.com"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full py-2.5 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isLoading && <Spinner size="sm" />}
              {isLoading ? "Sending…" : "Send reset link"}
            </button>

            <p className="text-center text-sm text-muted-foreground">
              <Link
                href="/login"
                className="text-primary hover:text-primary/80 font-medium transition-colors"
              >
                Back to sign in
              </Link>
            </p>
          </form>
        )}
      </section>
    </main>
  );
}
