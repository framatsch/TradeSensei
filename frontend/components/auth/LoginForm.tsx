/**
 * LoginForm — username + password login form.
 */

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useLogin } from "@/hooks/useAuth";
import { Spinner } from "@/components/ui/Spinner";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import { OIDCSignInButton } from "@/components/auth/OIDCSignInButton";
import { useAuthConfig } from "@/hooks/useAuth";
import { extractApiError } from "@/lib/apiErrors";

export function LoginForm() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const { mutate: login, isPending, error } = useLogin();

  const errorMessage = (() => {
    if (!error) return null;
    return extractApiError(error, "Login failed. Please check your credentials.");
  })();

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    login({ username, password });
  };

  const { data: authConfig } = useAuthConfig();
  const localAuthEnabled = authConfig?.local_auth_enabled ?? true;
  const passwordResetEnabled = authConfig?.password_reset_enabled ?? false;
  const showDivider = localAuthEnabled && (authConfig?.google_enabled || authConfig?.oidc?.enabled);

  // Auto-redirect when local auth is disabled and exactly one provider is active.
  useEffect(() => {
    if (!authConfig || localAuthEnabled) return;
    const hasGoogle = authConfig.google_enabled;
    const hasOidc = authConfig.oidc?.enabled;
    if (hasGoogle && !hasOidc) {
      window.location.href = "/api/proxy/api/v1/auth/google";
    } else if (hasOidc && !hasGoogle) {
      window.location.href = "/api/proxy/api/v1/auth/oidc";
    }
    // If both providers are active: show provider buttons, no auto-redirect.
  }, [authConfig, localAuthEnabled]);

  return (
    <div className="space-y-4">
      {localAuthEnabled && (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="username"
              className="block text-sm font-medium text-muted-foreground mb-1"
            >
              Username or Email
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 bg-secondary border border-border dark:border-border rounded-md text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label
                htmlFor="password"
                className="block text-sm font-medium text-muted-foreground"
              >
                Password
              </label>
              {passwordResetEnabled && (
                <Link
                  href="/forgot-password"
                  className="text-xs text-primary hover:text-primary/80 font-medium transition-colors"
                >
                  Forgot password?
                </Link>
              )}
            </div>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 bg-secondary border border-border dark:border-border rounded-md text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>

          {errorMessage && (
            <p className="text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-md px-3 py-2">
              {errorMessage}
            </p>
          )}

          <button
            type="submit"
            disabled={isPending}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary hover:bg-primary/90 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium rounded-md transition-colors"
          >
            {isPending && <Spinner size="sm" />}
            {isPending ? "Signing in…" : "Sign In"}
          </button>
        </form>
      )}

      {/* Divider — only between local form and external buttons */}
      {showDivider && (
        <div className="relative flex items-center gap-3">
          <div className="flex-1 border-t border-border" />
          <span className="text-xs text-muted-foreground select-none">or</span>
          <div className="flex-1 border-t border-border" />
        </div>
      )}

      {/* External sign-in buttons */}
      <div className="space-y-3">
        <GoogleSignInButton />
        <OIDCSignInButton />
      </div>

      {/* Register link — hidden when local auth is disabled */}
      {localAuthEnabled && (
        <p className="text-center text-sm text-muted-foreground mt-6">
          Don&apos;t have an account?{" "}
          <Link
            href="/register"
            className="text-primary hover:text-primary/80 font-medium transition-colors"
          >
            Create one
          </Link>
        </p>
      )}
    </div>
  );
}
