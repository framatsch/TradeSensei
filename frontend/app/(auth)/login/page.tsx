import { Suspense } from "react";
import Link from "next/link";
import { LoginForm } from "@/components/auth/LoginForm";
import { OAuthErrorBanner } from "@/components/auth/OAuthErrorBanner";

export const metadata = {
  title: "Sign In — Trade Journal",
};

export default function LoginPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 px-4">
      <div className="w-full max-w-md">
        {/* Logo / title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-600 mb-4">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="w-6 h-6 text-white"
            >
              <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
              <polyline points="16 7 22 7 22 13" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Trade Journal</h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">
            Sign in to your account
          </p>
        </div>

        {/* Form card */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-8">
          {/* OAuth error banner — shown when redirected back from a failed OAuth flow */}
          <Suspense>
            <OAuthErrorBanner />
          </Suspense>

          <LoginForm />

          <p className="text-center text-sm text-slate-600 dark:text-slate-400 mt-6">
            Don&apos;t have an account?{" "}
            <Link
              href="/register"
              className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium"
            >
              Create one
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
