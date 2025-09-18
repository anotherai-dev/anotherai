"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { CompletionsTable } from "@/app/completions/sections/table/CompletionsTable";
import { LoadingState } from "@/components/LoadingState";
import { PageError } from "@/components/PageError";
import { PageHeader } from "@/components/PageHeader";
import { useToast } from "@/components/ToastProvider";
import { useCompletionsListSync } from "@/hooks/useCompletionsListSync";
import { useCompletionsQuery } from "@/store/completions";
import { useDeployments, useOrFetchDeployment } from "@/store/deployments";
import { ArchiveDeploymentModal } from "./components/DeleteDeploymentModal";
import { DeploymentInfoSection } from "./components/DeploymentInfoSection";
import { DeploymentInfoTooltip } from "./components/DeploymentInfoTooltip";

export default function DeploymentDetailPage() {
  const params = useParams();
  // URL decode the deployment ID to handle special characters like : and #
  // e.g., "politician-qa%3Aproduction%231" becomes "politician-qa:production#1"
  const deploymentId = decodeURIComponent(params.id as string);

  const router = useRouter();
  const { showToast } = useToast();
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const { deployment, isLoading, error } = useOrFetchDeployment(deploymentId);
  const archiveDeployment = useDeployments((state) => state.archiveDeployment);

  // Fetch completions for this specific deployment
  const completionsQuery = `SELECT id, input_messages, input_variables, output_messages, output_error, updated_at as date FROM completions WHERE metadata['anotherai/deployment_id'] = '${deploymentId}' ORDER BY created_at DESC LIMIT 20`;
  const {
    data: completionsData,
    isLoading: isLoadingCompletions,
    error: completionsError,
  } = useCompletionsQuery(completionsQuery);

  // Sync completions data with stored completions list for modal navigation
  useCompletionsListSync(completionsData);

  const handleDeleteClick = () => {
    setIsDeleteModalOpen(true);
  };

  const handleDeleteConfirm = async () => {
    setIsDeleting(true);
    try {
      await archiveDeployment(deploymentId);
      showToast("Deployment archived successfully");
      router.push("/deployments");
    } catch (error) {
      console.error("Failed to delete deployment:", error);
      showToast("Failed to archive deployment");
    } finally {
      setIsDeleting(false);
      setIsDeleteModalOpen(false);
    }
  };

  if (isLoading || (!deployment && !error)) {
    return (
      <div className="flex flex-col w-full h-full mx-auto px-4 py-8 bg-gray-50 overflow-y-auto">
        <LoadingState />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col w-full h-full mx-auto px-4 py-8 bg-gray-50 overflow-y-auto">
        <PageError error={error.message} />
      </div>
    );
  }

  if (!deployment) {
    return (
      <div className="flex flex-col w-full h-full mx-auto px-4 py-8 bg-gray-50 overflow-y-auto">
        <PageError error="Deployment not found" />
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full min-h-full mx-auto px-4 py-8 bg-gray-50">
      <PageHeader
        breadcrumbs={[{ label: "Deployments", href: "/deployments" }, { label: deploymentId }]}
        title={deployment.id}
        copyablePrefixAndId={`anotherai/deployment/${deploymentId}`}
        className="mb-4"
        rightContent={
          <button
            onClick={handleDeleteClick}
            className="px-3 py-1.5 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-[2px] transition-colors cursor-pointer"
          >
            Archive Deployment
          </button>
        }
        descriptionBottomContent={<DeploymentInfoTooltip deploymentId={deploymentId} agentId={deployment.agent_id} />}
      />
      <DeploymentInfoSection deployment={deployment} />
      <div>
        <CompletionsTable
          data={completionsData ?? []}
          isLoading={isLoadingCompletions}
          error={completionsError}
          heightForEmptyState="120px"
          maxHeight="600px"
        />
      </div>

      <ArchiveDeploymentModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        deploymentId={deploymentId}
        onConfirm={handleDeleteConfirm}
        isLoading={isDeleting}
      />
    </div>
  );
}
