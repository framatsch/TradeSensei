/**
 * Root page — redirect to /dashboard if token present, else /login.
 */

import { redirect } from "next/navigation";

export default function RootPage() {
  // Server component: can't read localStorage, so redirect to dashboard.
  // Dashboard layout handles the auth guard for unauthenticated users.
  redirect("/dashboard");
}
