/**
 * PasswordResetSuccessBanner — reads the `?reset=success` query parameter and
 * shows a confirmation message when the user arrives at the login page after a
 * successful password reset.
 */

"use client";

import { useSearchParams } from "next/navigation";
import { CheckCircle2 } from "lucide-react";

export function PasswordResetSuccessBanner() {
  const searchParams = useSearchParams();
  const reset = searchParams.get("reset");

  if (reset !== "success") return null;

  return (
    <div
      className="mb-4 flex items-center gap-2 rounded-md border px-3 py-2 text-sm text-foreground"
      style={{
        backgroundColor: "color-mix(in srgb, var(--success) 10%, transparent)",
        borderColor: "color-mix(in srgb, var(--success) 30%, transparent)",
      }}
    >
      <CheckCircle2 className="h-4 w-4 text-success" />
      <span>Your password has been reset. You can now sign in.</span>
    </div>
  );
}
