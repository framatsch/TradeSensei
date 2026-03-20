/**
 * Connections page — redirects to /dashboard/settings.
 *
 * Broker connection management has been consolidated into the Settings page
 * under the "Accounts & Integrations" tab.
 */

import { redirect } from "next/navigation";

export default function ConnectionsPage() {
  redirect("/dashboard/settings");
}
