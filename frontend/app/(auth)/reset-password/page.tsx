"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
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
          className="w-full px-3 py-2 bg-secondary border border-border rounded-md text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
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
          className="w-full px-3 py-2 bg-secondary border border-border rounded-md text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
        />
      </div>

      {errorMessage && (
        <p className="text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-md px-3 py-2">
          {errorMessage}{" "}
          {errorMessage.includes("expired") && (
            <Link
              href="/forgot-password"
              className="underline hover:text-red-300 transition-colors"
            >
              Request a new link
            </Link>
          )}
        </p>
      )}

      <button
        type="submit"
        disabled={isLoading}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary hover:bg-primary/90 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium rounded-md transition-colors"
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
    <main className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="flex flex-col items-center mb-8">
          <Image
            src="/logo.svg"
            alt="Trade Sensei logo"
            width={512}
            height={512}
            priority
            className="rounded-xl mb-4"
            style={{ width: "auto", maxWidth: "100%", height: "auto", maxHeight: "10rem" }}
          />
          <h1 className="text-2xl font-bold text-foreground mb-1 tracking-tight">
            Trade Sensei
          </h1>
          <p className="text-muted-foreground text-sm">Set a new password</p>
        </div>

        {/* Card */}
        <div className="bg-card rounded-2xl border border-border p-8 shadow-sm">
          <Suspense fallback={<Spinner size="sm" />}>
            <ResetPasswordForm />
          </Suspense>
        </div>
      </div>
    </main>
  );
}
