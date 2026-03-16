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
import apiClient from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { Spinner } from "@/components/ui/Spinner";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import type { ResponseEnvelope, TokenResponse, User, UserCreate } from "@/lib/types";
import type { AxiosError } from "axios";

export function RegisterForm() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const setToken = useAuthStore((s) => s.setToken);
  const setUser = useAuthStore((s) => s.setUser);
  const queryClient = useQueryClient();
  const router = useRouter();

  const { mutate: register, isPending, error } = useMutation<User, Error, UserCreate>({
    mutationFn: async (payload: UserCreate) => {
      const res = await apiClient.post<ResponseEnvelope<User>>(
        "/api/v1/auth/register",
        payload
      );
      return res.data.data;
    },
    onSuccess: async (user) => {
      // Auto-login after registration
      const params = new URLSearchParams();
      params.append("username", username);
      params.append("password", password);
      const tokenRes = await apiClient.post<TokenResponse>(
        "/api/v1/auth/token",
        params,
        { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
      );
      setToken(tokenRes.data.access_token);
      setUser(user);
      await queryClient.invalidateQueries({ queryKey: ["currentUser"] });
      router.push("/dashboard");
    },
  });

  const errorMessage = (() => {
    if (!error) return null;
    const axiosErr = error as AxiosError<{ detail?: string }>;
    return (
      axiosErr.response?.data?.detail ??
      "Registration failed. Please try again."
    );
  })();

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    register({ username, email, password });
  };

  return (
    <div className="space-y-4">
      {/* Google sign-in */}
      <GoogleSignInButton />

      {/* Divider */}
      <div className="relative flex items-center gap-3">
        <div className="flex-1 border-t border-slate-700" />
        <span className="text-xs text-slate-500 select-none">or</span>
        <div className="flex-1 border-t border-slate-700" />
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label
          htmlFor="username"
          className="block text-sm font-medium text-slate-300 mb-1"
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
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="alice"
        />
      </div>

      <div>
        <label
          htmlFor="email"
          className="block text-sm font-medium text-slate-300 mb-1"
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
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="alice@example.com"
        />
      </div>

      <div>
        <label
          htmlFor="password"
          className="block text-sm font-medium text-slate-300 mb-1"
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
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="••••••••"
        />
        <p className="text-xs text-slate-500 mt-1">Minimum 8 characters.</p>
      </div>

      {errorMessage && (
        <p className="text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-md px-3 py-2">
          {errorMessage}
        </p>
      )}

      <button
        type="submit"
        disabled={isPending}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium rounded-md transition-colors"
      >
        {isPending && <Spinner size="sm" />}
        {isPending ? "Creating account…" : "Create Account"}
      </button>
    </form>
    </div>
  );
}
