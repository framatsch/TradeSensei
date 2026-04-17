"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import apiClient from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await apiClient.post("/api/v1/auth/forgot-password", { email });
    } catch {
      // Intentionally ignore errors — always show the success message
      // to prevent user enumeration.
    } finally {
      setIsLoading(false);
      setSubmitted(true);
    }
  };

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
          <p className="text-muted-foreground text-sm">Reset your password</p>
        </div>

        {/* Card */}
        <div className="bg-card rounded-2xl border border-border p-8 shadow-sm">
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
                  className="w-full px-3 py-2 bg-secondary border border-border rounded-md text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="you@example.com"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary hover:bg-primary/90 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium rounded-md transition-colors"
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
        </div>
      </div>
    </main>
  );
}
