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

import { useAuthConfig } from "@/hooks/useAuth";

export function OIDCSignInButton() {
  const { data: config } = useAuthConfig();
  
  if (!config?.oidc?.enabled) return null;

  const handleClick = () => {
    // Route through the Next.js proxy
    window.location.href = "/api/proxy/api/v1/auth/oidc";
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className="w-full flex items-center justify-center gap-3 px-4 py-2.5 bg-white hover:bg-gray-50 active:bg-gray-100 text-gray-700 font-medium rounded-md border border-gray-300 transition-colors shadow-sm"
    >
      Continue with {config.oidc.provider_name}
    </button>
  );
}
