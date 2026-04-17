/**
 * PasswordResetSuccessBanner — reads the `?reset=success` query parameter and
 * shows a confirmation message when the user arrives at the login page after a
 * successful password reset.
 */

"use client";

import { useSearchParams } from "next/navigation";

export function PasswordResetSuccessBanner() {
  const searchParams = useSearchParams();
  const reset = searchParams.get("reset");

  if (reset !== "success") return null;

  return (
    <div className="mb-4 text-sm text-green-400 bg-green-900/20 border border-green-800 rounded-md px-3 py-2">
      Your password has been reset. You can now sign in.
    </div>
  );
}
