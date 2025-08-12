"use client";

import { Copy, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo, useState } from "react";
import { useOrFetchAnnotations } from "@/store/annotations";
import { useOrFetchCompletion } from "@/store/completion";
import { LoadingIndicator } from "../LoadingIndicator";
import { Modal } from "../Modal";
import { PersistantAllotment } from "../PersistantAllotment";
import { useToast } from "../ToastProvider";
import { CompletionContextView } from "./CompletionContextView";
import { CompletionConversationView } from "./CompletionConversationView";
import { CompletionDetailsView } from "./CompletionDetailsView";
import { CompletionNavigationButtons } from "./CompletionNavigationButtons";

export function CompletionModal() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { showToast } = useToast();

  const completionId = searchParams.get("showCompletionModal") ?? undefined;
  const isOpen = !!completionId;

  const { completion } = useOrFetchCompletion(completionId);
  const { annotations } = useOrFetchAnnotations({
    completion_id: completionId,
  });

  const [keypathSelected, setKeypathSelected] = useState<string | null>(null);

  const hasInputVariables = useMemo(() => {
    return (
      completion?.input?.variables &&
      Object.keys(completion.input.variables).length > 0
    );
  }, [completion?.input?.variables]);

  const closeModal = useCallback(() => {
    const params = new URLSearchParams(searchParams);
    params.delete("showCompletionModal");
    const newUrl = `${window.location.pathname}${
      params.toString() ? `?${params.toString()}` : ""
    }`;
    router.replace(newUrl, { scroll: false });
  }, [searchParams, router]);

  const copyCompletionId = useCallback(() => {
    if (completionId) {
      navigator.clipboard.writeText(`anotherai/completion/${completionId}`);
      showToast("Copied completion id!");
    }
  }, [completionId, showToast]);

  if (!completionId) {
    return null;
  }

  return (
    <Modal isOpen={isOpen} onClose={closeModal}>
      <div className="flex flex-col w-[90vw] h-[90vh] bg-slate-50 rounded-[2px] border border-gray-200 shadow-lg shadow-black/20">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 border-dashed">
          <div className="flex items-center gap-3">
            <button
              onClick={closeModal}
              className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer px-2 py-1 rounded-[2px] w-8 h-8 flex items-center justify-center shadow-sm shadow-black/5"
            >
              <X size={16} />
            </button>
            <h2 className="text-base font-bold">Completion Details</h2>
            <CompletionNavigationButtons completionId={completionId} />
          </div>
          <button
            onClick={copyCompletionId}
            className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer px-2 py-1 rounded-[2px] w-8 h-8 flex items-center justify-center shadow-sm shadow-black/5"
          >
            <Copy size={16} />
          </button>
        </div>

        {!completion ? (
          <div className="flex w-full h-full items-center justify-center">
            <LoadingIndicator />
          </div>
        ) : (
          <PersistantAllotment
            key={`ProxyRunView-PersistantAllotment-${hasInputVariables}`}
            name={`ProxyRunView-PersistantAllotment-${hasInputVariables}`}
            initialSize={hasInputVariables ? [100, 100, 100] : [200, 100]}
            className="flex w-full h-full"
          >
            {hasInputVariables && (
              <div className="flex flex-col h-full border-r border-dashed border-gray-200 overflow-hidden">
                <CompletionContextView completion={completion} />
              </div>
            )}
            <div className="flex flex-col h-full border-r border-dashed border-gray-200">
              <CompletionConversationView
                completion={completion}
                annotations={annotations}
                onKeypathSelect={setKeypathSelected}
              />
            </div>
            <div className="flex flex-col h-full">
              <CompletionDetailsView
                completion={completion}
                annotations={annotations}
                keypathSelected={keypathSelected}
                setKeypathSelected={setKeypathSelected}
              />
            </div>
          </PersistantAllotment>
        )}
      </div>
    </Modal>
  );
}
