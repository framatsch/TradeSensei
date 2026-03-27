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
