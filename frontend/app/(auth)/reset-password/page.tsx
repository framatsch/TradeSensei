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

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Logo } from "@/components/ui/Logo";
import { Spinner } from "@/components/ui/Spinner";
import { resetPasswordApiV1AuthResetPasswordPost } from "@/lib/api/index";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // If there is no token in the URL, redirect to the forgot-password page.
  if (!token) {
    router.replace("/forgot-password");
    return null;
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrorMessage(null);

    if (newPassword !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    setIsLoading(true);
    try {
      const { error, response } = await resetPasswordApiV1AuthResetPasswordPost({
        body: { token, new_password: newPassword },
      });
      if (error) {
        const status = response?.status;
        if (status === 401) {
          setErrorMessage(
            "This reset link has expired or has already been used. Please request a new one."
          );
        } else if (status === 422) {
          setErrorMessage("Password must be at least 8 characters.");
        } else {
          setErrorMessage("Something went wrong. Please try again.");
        }
        return;
      }
      router.push("/login?reset=success");
    } catch {
      setErrorMessage("Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Choose a new password for your account.
      </p>

      <div>
        <label
          htmlFor="new-password"
          className="block text-sm font-medium text-muted-foreground mb-1"
        >
          New password
        </label>
        <input
          id="new-password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          className="w-full px-3 py-2 bg-secondary border border-border rounded-md text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
        />
      </div>

      <div>
        <label
          htmlFor="confirm-password"
          className="block text-sm font-medium text-muted-foreground mb-1"
        >
          Confirm new password
        </label>
        <input
          id="confirm-password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          className="w-full px-3 py-2 bg-secondary border border-border rounded-md text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
        />
      </div>

      {errorMessage && (
        <p className="text-sm text-danger surface-danger border rounded-md px-3 py-2">
          {errorMessage}{" "}
          {errorMessage.includes("expired") && (
            <Link
              href="/forgot-password"
              className="underline hover:text-danger/80 transition-colors"
            >
              Request a new link
            </Link>
          )}
        </p>
      )}

      <button
        type="submit"
        disabled={isLoading}
        className="btn-primary w-full py-2.5 disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {isLoading && <Spinner size="sm" />}
        {isLoading ? "Saving…" : "Set new password"}
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
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-lg items-center p-4">
      <section className="solid-card w-full space-y-4 p-6">
        <div className="flex flex-col items-center gap-3 text-center">
          <Logo size={72} className="rounded-2xl" />
          <h1 className="text-2xl font-semibold text-foreground">
            Set a new password
          </h1>
        </div>

        <Suspense fallback={<Spinner size="sm" />}>
          <ResetPasswordForm />
        </Suspense>
      </section>
    </main>
  );
}
