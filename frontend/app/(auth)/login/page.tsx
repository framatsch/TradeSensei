import { Suspense } from "react";
import { LoginForm } from "@/components/auth/LoginForm";
import { OAuthErrorBanner } from "@/components/auth/OAuthErrorBanner";
import { LoginHeader } from "@/components/auth/LoginHeader";

export const metadata = {
  title: "Sign In — Trade Sensei",
};

export default function LoginPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">
        <LoginHeader />

        {/* Form card */}
        <div className="bg-card rounded-2xl border border-border p-8 shadow-sm">
          {/* OAuth error banner — shown when redirected back from a failed OAuth flow */}
          <Suspense>
            <OAuthErrorBanner />
          </Suspense>

          <LoginForm />
        </div>
      </div>
    </main>
  );
}
