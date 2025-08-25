"use client";

import { useRouter } from "next/navigation";
import { use, useCallback } from "react";
import { LoadingIndicator } from "@/components/LoadingIndicator";
import { PageHeader } from "@/components/PageHeader";
import { useToast } from "@/components/ToastProvider";
import { CompareVersionsView } from "@/components/deployment-modal/components/CompareVersionsView";
import { useOrFetchCompletion } from "@/store/completion";
import { useNewestCompletionId } from "@/store/completions";

interface DeploymentPageProps {
  params: Promise<{
    completion_id: string;
  }>;
}

export default function DeploymentPage({ params }: DeploymentPageProps) {
  const { showToast } = useToast();
  const router = useRouter();
  const { completion_id } = use(params);
  const completionId = completion_id;

  // Fetch specific completion using the completion_id from URL
  const { completion: specificCompletion, isLoading: isLoadingSpecific } = useOrFetchCompletion(completionId);
  const { newestCompletionId, isLoading: isLoadingNewest } = useNewestCompletionId();

  // Always fetch the newest completion for the currently deployed version
  const { completion: newestCompletion, isLoading: isLoadingNewestCompletion } = useOrFetchCompletion(
    newestCompletionId ?? undefined
  );

  const isLoading = isLoadingSpecific || isLoadingNewest || isLoadingNewestCompletion;

  // Extract versions
  const versionToBeDeployed = specificCompletion?.version;
  const versionCurrentlyDeployed = newestCompletion?.version;

  const handleConfirmDeploy = useCallback(() => {
    showToast(`Deployed`);
    router.push("/");
  }, [showToast, router]);

  const handleCancel = useCallback(() => {
    router.push("/");
  }, [router]);

  return (
    <div className="flex flex-col w-full h-screen bg-gray-50">
      <div className="px-4 pt-8">
        <PageHeader
          breadcrumbs={[{ label: "Home", href: "/" }, { label: "Deployments" }, { label: completionId }]}
          title="Deployment"
          copyablePrefixAndId={`anotherai/deployment/${completionId}`}
          className="mb-2"
        />
      </div>

      {isLoading ? (
        <div className="flex w-full h-full items-center justify-center">
          <LoadingIndicator />
        </div>
      ) : (
        <>
          <div className="flex-1 overflow-auto">
            <CompareVersionsView
              versionCurrentlyDeployed={versionCurrentlyDeployed}
              versionToBeDeployed={versionToBeDeployed}
            />
          </div>
          <div className="flex justify-between items-center px-4 py-4 border-t border-gray-200 bg-white">
            <button
              onClick={handleCancel}
              className="bg-gray-100 text-gray-700 hover:bg-gray-200 cursor-pointer px-4 py-2 rounded-[2px] font-bold text-[13px] shadow-sm shadow-black/5"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirmDeploy}
              className="bg-indigo-500 text-white hover:bg-indigo-600 cursor-pointer px-4 py-2 rounded-[2px] font-bold text-[13px] shadow-sm shadow-black/5"
            >
              Confirm Deploy
            </button>
          </div>
        </>
      )}
    </div>
  );
}
