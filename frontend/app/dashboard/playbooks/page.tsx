import { redirect } from "next/navigation";

export default function OldPlaybooksRedirect() {
  redirect("/dashboard/library/playbooks");
}
