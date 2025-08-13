"use client";

import { X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import { useOrFetchCompletion } from "@/store/completion";
import { useNewestCompletionId } from "@/store/completions";
import { LoadingIndicator } from "../LoadingIndicator";
import { Modal } from "../Modal";
import { useToast } from "../ToastProvider";
import { CompareVersionsView } from "./components/CompareVersionsView";

export function DeploymentModal() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { showToast } = useToast();

  const deploymentParam = searchParams.get("showDeploymentModal");
  const completionId = deploymentParam && deploymentParam !== "true" ? deploymentParam : undefined;
  const isOpen = !!deploymentParam;

  // Fetch specific completion if ID provided, otherwise get newest
  const { completion: specificCompletion, isLoading: isLoadingSpecific } = useOrFetchCompletion(completionId);
  const { newestCompletionId, isLoading: isLoadingNewest } = useNewestCompletionId();
  
  // Always fetch the newest completion for the currently deployed version
  const { completion: newestCompletion, isLoading: isLoadingNewestCompletion } = useOrFetchCompletion(newestCompletionId ?? undefined);

  const isLoading = isLoadingSpecific || isLoadingNewest || isLoadingNewestCompletion;

  // Extract versions
  const versionToBeDeployed = specificCompletion?.version;
  const versionCurrentlyDeployed = newestCompletion?.version;

  const closeModal = useCallback(() => {
    const params = new URLSearchParams(searchParams);
    params.delete("showDeploymentModal");
    const newUrl = `${window.location.pathname}${
      params.toString() ? `?${params.toString()}` : ""
    }`;
    router.replace(newUrl, { scroll: false });
  }, [searchParams, router]);

  const handleConfirmDeploy = useCallback(() => {
    showToast(`Deployed`);
    closeModal();
  }, [showToast, closeModal]);

  if (!isOpen) {
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
            <h2 className="text-base font-bold">Confirm Deployment</h2>
          </div>
          <button
            onClick={handleConfirmDeploy}
            className="bg-indigo-500 text-white hover:bg-indigo-600 cursor-pointer px-4 py-2 rounded-[2px] font-bold text-[13px] shadow-sm shadow-black/5"
          >
            Confirm Deploy
          </button>
        </div>

        {isLoading ? (
          <div className="flex w-full h-full items-center justify-center">
            <LoadingIndicator />
          </div>
        ) : (
          <CompareVersionsView
            versionCurrentlyDeployed={versionCurrentlyDeployed}
            versionToBeDeployed={versionToBeDeployed}
          />
        )}
      </div>
    </Modal>
  );
}