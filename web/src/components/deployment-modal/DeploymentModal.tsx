"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import { Modal } from "../Modal";
import { DeploymentContent } from "./DeploymentContent";

interface DeploymentModalProps {
  isOpen?: boolean;
  onClose?: () => void;
  deploymentId?: string;
  completionId?: string;
}

export function DeploymentModal({
  isOpen: isOpenProp,
  onClose: onCloseProp,
  deploymentId: deploymentIdProp,
  completionId: completionIdProp,
}: DeploymentModalProps = {}) {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Support both URL params (legacy) and props (new)
  const deploymentParam = searchParams.get("showDeploymentModal");
  const urlCompletionId = deploymentParam && deploymentParam !== "true" ? deploymentParam : undefined;
  const urlDeploymentId = searchParams.get("deployment_id");
  const urlCompletionIdFromParam = searchParams.get("completion_id");

  // Use props first, then fall back to URL params
  const deploymentId = deploymentIdProp || (urlDeploymentId ? decodeURIComponent(urlDeploymentId) : undefined);
  const completionId = completionIdProp || urlCompletionIdFromParam || urlCompletionId;
  const isOpen = isOpenProp !== undefined ? isOpenProp : !!deploymentParam;

  const closeModal = useCallback(() => {
    if (onCloseProp) {
      onCloseProp();
    } else {
      const params = new URLSearchParams(searchParams);
      params.delete("showDeploymentModal");
      params.delete("deployment_id");
      params.delete("completion_id");
      const newUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}`;
      router.replace(newUrl, { scroll: false });
    }
  }, [onCloseProp, searchParams, router]);

  if (!isOpen) {
    return null;
  }

  return (
    <Modal isOpen={isOpen} onClose={closeModal}>
      <div className="w-[90vw] h-[90vh]">
        <DeploymentContent
          deploymentId={deploymentId}
          completionId={completionId}
          onClose={closeModal}
          showConfirmButton={true}
        />
      </div>
    </Modal>
  );
}
