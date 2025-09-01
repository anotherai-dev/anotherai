"use client";

import { X } from "lucide-react";
import { useOrFetchCompletion } from "@/store/completion";
import { useNewestCompletionId } from "@/store/completions";
import { useOrFetchDeployment } from "@/store/deployments";
import { LoadingIndicator } from "../LoadingIndicator";
import { useToast } from "../ToastProvider";
import { CompareVersionsView } from "./components/CompareVersionsView";

interface DeploymentContentProps {
  deploymentId?: string;
  completionId?: string;
  onClose?: () => void;
  showConfirmButton?: boolean;
}

export function DeploymentContent({
  deploymentId,
  completionId,
  onClose,
  showConfirmButton = true,
}: DeploymentContentProps) {
  const { showToast } = useToast();

  // Fetch deployment and completion data
  const { deployment, isLoading: isLoadingDeployment } = useOrFetchDeployment(deploymentId || "");
  const { completion, isLoading: isLoadingCompletion } = useOrFetchCompletion(completionId);

  // Fallback to old behavior if no deployment ID provided
  const { newestCompletionId, isLoading: isLoadingNewest } = useNewestCompletionId();
  const { completion: newestCompletion, isLoading: isLoadingNewestCompletion } = useOrFetchCompletion(
    !deploymentId ? (newestCompletionId ?? undefined) : undefined
  );

  const isLoading = isLoadingDeployment || isLoadingCompletion || isLoadingNewest || isLoadingNewestCompletion;

  // Extract versions - deployment version (left), completion version (right)
  const versionCurrentlyDeployed = deployment?.version || newestCompletion?.version;
  const versionToBeDeployed = completion?.version;

  const handleConfirmDeploy = () => {
    showToast(`Deployed`);
    onClose?.();
  };

  return (
    <div className="flex flex-col w-full h-full bg-slate-50 rounded-[2px] border border-gray-200 shadow-lg shadow-black/20">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 border-dashed">
        <div className="flex items-center gap-3">
          {onClose && (
            <button
              onClick={onClose}
              className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer px-2 py-1 rounded-[2px] w-8 h-8 flex items-center justify-center shadow-sm shadow-black/5"
            >
              <X size={16} />
            </button>
          )}
          <h2 className="text-base font-bold">Confirm Deployment</h2>
        </div>
        {showConfirmButton && (
          <button
            onClick={handleConfirmDeploy}
            className="bg-indigo-500 text-white hover:bg-indigo-600 cursor-pointer px-4 py-2 rounded-[2px] font-bold text-[13px] shadow-sm shadow-black/5"
          >
            Confirm Deploy
          </button>
        )}
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
  );
}
