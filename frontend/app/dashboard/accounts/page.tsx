/**
 * Accounts page — redirects to /dashboard/settings.
 *
 * Account management has been consolidated into the Settings page
 * under the "Accounts & Integrations" tab.
 */

import { redirect } from "next/navigation";

export default function AccountsPage() {
  redirect("/dashboard/settings");
}
