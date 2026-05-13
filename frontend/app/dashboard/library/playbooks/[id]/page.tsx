import { PlaybookEditorClient } from "@/components/playbooks/PlaybookEditorClient";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function PlaybookEditorPage({ params }: Props) {
  const { id } = await params;
  return <PlaybookEditorClient id={id} />;
}
