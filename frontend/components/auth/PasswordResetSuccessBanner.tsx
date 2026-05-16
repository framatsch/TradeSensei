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
