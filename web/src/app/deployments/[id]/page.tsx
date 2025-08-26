"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { CompletionsTable } from "@/app/completions/sections/table/CompletionsTable";
import { LoadingIndicator } from "@/components/LoadingIndicator";
import { PageError } from "@/components/PageError";
import { PageHeader } from "@/components/PageHeader";
import { useToast } from "@/components/ToastProvider";
import { useCompletionsListSync } from "@/hooks/useCompletionsListSync";
import { useCompletionsQuery } from "@/store/completions";
import { useMockedDeployments, useOrFetchMockedDeployment } from "@/store/mocked_deployments";
import { DeleteDeploymentModal } from "./components/DeleteDeploymentModal";
import { DeploymentInfoSection } from "./components/DeploymentInfoSection";

export default function DeploymentDetailPage() {
  const params = useParams();
  const deploymentId = params.id as string;

  const router = useRouter();
  const { showToast } = useToast();
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const { deployment, isLoading, error } = useOrFetchMockedDeployment(deploymentId);
  const deleteDeployment = useMockedDeployments((state) => state.deleteDeployment);

  // Fetch completions with only id, input, output, and date fields
  const completionsQuery = `SELECT id, input_messages, input_variables, output_messages, output_error, updated_at as date FROM completions ORDER BY created_at DESC LIMIT 100`;
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
      await deleteDeployment(deploymentId);
      showToast("Deployment deleted successfully");
      router.push("/deployments");
    } catch (error) {
      console.error("Failed to delete deployment:", error);
      showToast("Failed to delete deployment");
    } finally {
      setIsDeleting(false);
      setIsDeleteModalOpen(false);
    }
  };

  if (error) {
    return (
      <div className="flex flex-col w-full h-full mx-auto px-4 py-8 bg-gray-50 overflow-y-auto">
        <PageError error={error.message} />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-col w-full h-full mx-auto px-4 py-8 bg-gray-50 overflow-y-auto">
        <div className="bg-white border border-gray-200 rounded-lg p-8 text-center">
          <LoadingIndicator />
        </div>
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
    <div className="flex flex-col w-full h-full mx-auto px-4 py-8 bg-gray-50 overflow-hidden">
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
            Delete Deployment
          </button>
        }
      />
      <DeploymentInfoSection deployment={deployment} />
      <div className="flex-1 flex flex-col min-h-0">
        <CompletionsTable data={completionsData ?? []} isLoading={isLoadingCompletions} error={completionsError} />
      </div>

      <DeleteDeploymentModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        deploymentId={deploymentId}
        onConfirm={handleDeleteConfirm}
        isLoading={isDeleting}
      />
    </div>
  );
}
