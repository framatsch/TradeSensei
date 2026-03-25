/**
 * GoogleSignInButton — initiates the Google OAuth flow by redirecting the
 * browser to the backend's authorization endpoint.
 *
 * The backend owns the full Authorization Code Flow; this button simply
 * navigates to `GET /api/proxy/v1/auth/google` which the Next.js proxy
 * forwards to the internal backend service.  The backend then redirects
 * to Google and ultimately back to `/auth/callback`.
 */

"use client";

/** Google "G" logo SVG (official brand colours). */
function GoogleLogo() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      aria-hidden="true"
      focusable="false"
    >
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.964 10.71c-.18-.54-.282-1.117-.282-1.71s.102-1.17.282-1.71V4.958H.957C.347 6.173 0 7.548 0 9s.348 2.827.957 4.042l3.007-2.332z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"
      />
    </svg>
  );
}

export function GoogleSignInButton() {
  const handleClick = () => {
    // Route through the Next.js proxy — backend is not publicly exposed.
    window.location.href = "/api/proxy/v1/auth/google";
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className="w-full flex items-center justify-center gap-3 px-4 py-2.5 bg-white hover:bg-gray-50 active:bg-gray-100 text-gray-700 font-medium rounded-md border border-gray-300 transition-colors shadow-sm"
    >
      <GoogleLogo />
      Continue with Google
    </button>
  );
}
