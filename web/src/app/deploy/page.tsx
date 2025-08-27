"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect } from "react";
import { LoadingIndicator } from "@/components/LoadingIndicator";
import { PageHeader } from "@/components/PageHeader";
import { useToast } from "@/components/ToastProvider";
import { CompareVersionsView } from "@/components/deployment-modal/components/CompareVersionsView";
import { useOrFetchCompletion } from "@/store/completion";
import { useDeployments, useOrFetchDeployment } from "@/store/deployments";

function DeployPageContent() {
  const { showToast } = useToast();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { updateDeployment } = useDeployments();

  // Get parameters using standard search params
  const deploymentIdParam = searchParams.get("deployment_id");
  const completionId = searchParams.get("completion_id");

  // Handle URL decoding for deployment ID
  const deploymentId = deploymentIdParam ? decodeURIComponent(deploymentIdParam) : null;

  // Fetch deployment and completion data
  const { deployment, isLoading: isLoadingDeployment } = useOrFetchDeployment(deploymentId || "");
  const { completion, isLoading: isLoadingCompletion } = useOrFetchCompletion(completionId || undefined);

  const isLoading = isLoadingDeployment || isLoadingCompletion;

  // Extract versions - deployment version (left), completion version (right)
  const versionCurrentlyDeployed = deployment?.version;
  const versionToBeDeployed = completion?.version;

  // Redirect to home if no parameters provided
  useEffect(() => {
    if (!deploymentId || !completionId) {
      router.replace("/");
    }
  }, [deploymentId, completionId, router]);

  const handleConfirmDeploy = useCallback(async () => {
    if (!deploymentId || !versionToBeDeployed) {
      showToast("Missing deployment or version information");
      return;
    }

    try {
      console.log(`Attempting to deploy: deploymentId=${deploymentId}`);
      console.log(`Completion:`, completion);
      await updateDeployment(deploymentId, { version: versionToBeDeployed });
      showToast("Version deployed successfully!");
      router.push("/deployments");
    } catch (error) {
      console.error("Failed to deploy version:", error);
      showToast("Failed to deploy version");
    }
  }, [deploymentId, versionToBeDeployed, completion, updateDeployment, showToast, router]);

  const handleCancel = useCallback(() => {
    router.push("/");
  }, [router]);

  if (!deploymentId || !completionId) {
    return null;
  }

  return (
    <div className="flex flex-col w-full h-screen bg-gray-50">
      <div className="px-4 pt-8">
        <PageHeader
          breadcrumbs={[{ label: "Home", href: "/" }, { label: "Deployments" }, { label: deploymentId }]}
          title="Deployment"
          copyablePrefixAndId={`anotherai/deployment/${deploymentId}`}
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

export default function DeployPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen w-screen bg-gray-50 items-center justify-center">
          <LoadingIndicator />
        </div>
      }
    >
      <DeployPageContent />
    </Suspense>
  );
}
