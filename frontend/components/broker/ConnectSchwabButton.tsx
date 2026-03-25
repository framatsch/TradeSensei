/**
 * ConnectSchwabButton — initiates the Schwab OAuth PKCE flow.
 *
 * Clicking the button navigates the browser to the backend
 * `GET /api/v1/broker/schwab/connect` endpoint, which redirects to
 * the Schwab authorization page.
 */

"use client";

const CONNECT_URL = "/api/v1/broker/schwab/connect";

interface Props {
  /** Optional extra CSS classes. */
  className?: string;
  /**
   * Navigation function — injectable for testing.
   * Defaults to `window.location.assign`.
   */
  navigate?: (url: string) => void;
}

export function ConnectSchwabButton({
  className = "",
  navigate = (url) => window.location.assign(url),
}: Props) {
  const handleConnect = () => {
    navigate(CONNECT_URL);
  };

  return (
    <button
      onClick={handleConnect}
      data-testid="connect-schwab-button"
      className={`inline-flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 active:bg-blue-800 text-white text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-zinc-900 ${className}`}
    >
      {/* Schwab-inspired "S" icon */}
      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-white/20 text-xs font-bold">
        S
      </span>
      Connect Schwab
    </button>
  );
}
