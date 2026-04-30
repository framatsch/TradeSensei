import { redirect } from "next/navigation";

export default function OldTagsRedirect() {
  redirect("/dashboard/library/tags");
}
