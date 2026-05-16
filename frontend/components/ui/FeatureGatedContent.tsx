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

"use client";

import Link from "next/link";

interface FeatureGatedContentProps {
  /** Display name shown in the locked message, e.g. "Risk Analytics". */
  featureName: string;
}

/**
 * Placeholder rendered in place of a page or tab when the required
 * feature flag is disabled for the current user.
 *
 * Provides a direct link to Settings → Features so the user can enable
 * the flag without having to navigate manually.
 */
export function FeatureGatedContent({ featureName }: FeatureGatedContentProps) {
  return (
    <div className="flex flex-col items-center justify-center py-32 gap-4 text-center">
      {/* Lock icon */}
      <div className="flex items-center justify-center w-12 h-12 rounded-full bg-muted border border-border">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="w-5 h-5 text-muted-foreground"
          aria-hidden="true"
        >
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      </div>

      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">{featureName} is not enabled</p>
        <p className="text-xs text-muted-foreground max-w-xs">
          This feature is currently disabled. Enable it in Settings to get access.
        </p>
      </div>

      <Link
        href="/dashboard/settings?tab=features"
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
      >
        Enable in Settings
      </Link>
    </div>
  );
}
