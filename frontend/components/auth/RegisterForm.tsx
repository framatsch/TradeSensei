/**
 * RegisterForm — username, email, and password registration form.
 *
 * After successful registration the backend returns the user, but we still
 * need a separate token call.  We chain a login mutation after the register
 * mutation to get the access token automatically.
 */

"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { Spinner } from "@/components/ui/Spinner";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import { OIDCSignInButton } from "@/components/auth/OIDCSignInButton";
import { useAuthConfig } from "@/hooks/useAuth";
import { extractApiError } from "@/lib/apiErrors";
import { registerApiV1AuthRegisterPost, loginApiV1AuthTokenPost } from "@/lib/api/index";
import type { ResponseEnvelope, User, UserCreate } from "@/lib/types";

export function RegisterForm() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const setToken = useAuthStore((s) => s.setToken);
  const setUser = useAuthStore((s) => s.setUser);
  const queryClient = useQueryClient();
  const router = useRouter();

  const { mutate: register, isPending, error } = useMutation<User, Error, UserCreate>({
    mutationFn: async (payload: UserCreate) => {
      const { data, error: regError } = await registerApiV1AuthRegisterPost({ body: payload });
      if (regError || !data) throw regError ?? new Error("Registration failed: no data returned");
      return (data as unknown as ResponseEnvelope<User>).data;
    },
    onSuccess: async (user) => {
      // Auto-login after registration
      const { data: tokenData, error: tokenError } = await loginApiV1AuthTokenPost({
        body: { username, password },
      });
      if (tokenError || !tokenData) throw tokenError ?? new Error("Login after registration failed");
      setToken(tokenData.access_token);
      setUser(user);
      await queryClient.invalidateQueries({ queryKey: ["currentUser"] });
      router.push("/dashboard");
    },
  });

  const errorMessage = (() => {
    if (validationError) return validationError;
    if (!error) return null;
    return extractApiError(error, "Registration failed. Please try again.");
  })();

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setValidationError(null);
    if (password !== confirmPassword) {
      setValidationError("Passwords do not match.");
      return;
    }
    register({ username, email, password });
  };

  const { data: authConfig } = useAuthConfig();
  const showDivider = authConfig?.google_enabled || authConfig?.oidc?.enabled;

  return (
    <div className="space-y-4">
      {/* External sign-in buttons */}
      <div className="space-y-3">
        <GoogleSignInButton />
        <OIDCSignInButton />
      </div>

      {/* Divider */}
      {showDivider && (
        <div className="relative flex items-center gap-3">
          <div className="flex-1 border-t border-border" />
          <span className="text-xs text-muted-foreground select-none">or</span>
          <div className="flex-1 border-t border-border" />
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label
          htmlFor="username"
          className="block text-sm font-medium text-muted-foreground mb-1"
        >
          Username
        </label>
        <input
          id="username"
          type="text"
          autoComplete="username"
          required
          minLength={3}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full px-3 py-2 bg-secondary border border-border dark:border-border rounded-md text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          placeholder="alice"
        />
      </div>

      <div>
        <label
          htmlFor="email"
          className="block text-sm font-medium text-muted-foreground mb-1"
        >
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-3 py-2 bg-secondary border border-border dark:border-border rounded-md text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          placeholder="alice@example.com"
        />
      </div>

      <div>
        <label
          htmlFor="password"
          className="block text-sm font-medium text-muted-foreground mb-1"
        >
          Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full px-3 py-2 bg-secondary border border-border dark:border-border rounded-md text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          placeholder="••••••••"
        />
        <p className="text-xs text-muted-foreground mt-1">Minimum 8 characters.</p>
      </div>

      <div>
        <label
          htmlFor="confirmPassword"
          className="block text-sm font-medium text-muted-foreground mb-1"
        >
          Confirm Password
        </label>
        <input
          id="confirmPassword"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          className="w-full px-3 py-2 bg-secondary border border-border dark:border-border rounded-md text-foreground placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          placeholder="••••••••"
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
        {isPending ? "Creating account…" : "Create Account"}
      </button>
    </form>
    </div>
  );
}
