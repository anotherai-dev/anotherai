"use client";

import { useParams } from "next/navigation";
import { CompletionModal } from "@/components/completion-modal/CompletionModal";
import CompletionsPage from "../page";

export const dynamic = "force-dynamic";

export default function CompletionPage() {
  const params = useParams();
  const completionId = params.id as string;

  return (
    <>
      <CompletionsPage />
      <CompletionModal completionId={completionId} isRouteModal={true} />
    </>
  );
}
