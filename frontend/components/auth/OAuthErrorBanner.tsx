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
 * OAuthErrorBanner — reads the `?error=` query parameter and displays a
 * user-friendly message when the Google OAuth flow fails or is cancelled.
 *
 * Rendered on the login page so errors from the backend redirect are visible.
 */

"use client";

import { useSearchParams } from "next/navigation";

const ERROR_MESSAGES: Record<string, string> = {
  oauth_cancelled: "Sign-in was cancelled. Please try again.",
  oauth_failed: "Sign-in failed. Please try again or use your password.",
  email_not_verified:
    "Your account email is not verified. Please verify it and try again.",
};

export function OAuthErrorBanner() {
  const searchParams = useSearchParams();
  const error = searchParams.get("error");

  if (!error) return null;

  const message =
    ERROR_MESSAGES[error] ??
    "An unexpected sign-in error occurred. Please try again.";

  return (
    <div className="mb-4 text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-md px-3 py-2">
      {message}
    </div>
  );
}
