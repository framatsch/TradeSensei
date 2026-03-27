import { redirect } from "next/navigation";

/**
 * Catch-all route for unknown paths under /dashboard/*.
 * Redirects to the dashboard overview instead of showing a 404.
 * Explicit routes (trades, analytics, cash, etc.) take precedence over
 * this catch-all and are never affected.
 */
export default function DashboardCatchAll() {
  redirect("/dashboard");
}
