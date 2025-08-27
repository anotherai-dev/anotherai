"use client";

import { X } from "lucide-react";
import { useState } from "react";
import { Modal } from "@/components/Modal";

interface ArchiveDeploymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  deploymentId: string;
  onConfirm: () => void;
  isLoading?: boolean;
}

// Keep the old export for backward compatibility
export const DeleteDeploymentModal = ArchiveDeploymentModal;

export function ArchiveDeploymentModal({
  isOpen,
  onClose,
  deploymentId,
  onConfirm,
  isLoading = false,
}: ArchiveDeploymentModalProps) {
  const [confirmationText, setConfirmationText] = useState("");
  const isConfirmationValid = confirmationText === deploymentId;

  const handleClose = () => {
    setConfirmationText("");
    onClose();
  };

  const handleConfirm = () => {
    if (isConfirmationValid) {
      setConfirmationText("");
      onConfirm();
    }
  };
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <div className="flex flex-col w-[500px] bg-white rounded-[2px] border border-gray-200 shadow-lg">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Archive Deployment</h2>
          <button
            onClick={handleClose}
            className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer px-2 py-1 rounded-[2px] w-8 h-8 flex items-center justify-center"
          >
            <X size={16} />
          </button>
        </div>

        <div className="px-4 py-6">
          <p className="text-sm text-gray-700 mb-2">
            <strong>Are you sure you want to archive this deployment?</strong>
          </p>
          <p className="text-sm text-gray-500 mb-6">
            The deployment will be archived and no longer appear in the list, but can still be used if referred to by
            ID.
          </p>
          <p className="text-sm text-gray-600 mb-2">
            Type <strong>{deploymentId}</strong> below to continue.
          </p>
          <input
            type="text"
            value={confirmationText}
            onChange={(e) => setConfirmationText(e.target.value)}
            placeholder={deploymentId}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-[2px] focus:outline-none focus:ring-1 focus:ring-gray-900 focus:border-gray-900"
          />
        </div>

        <div className="flex justify-end px-4 py-3 border-t border-gray-200">
          <button
            onClick={handleConfirm}
            disabled={!isConfirmationValid || isLoading}
            className={`px-3 py-1.5 text-sm font-medium text-white rounded-[2px] transition-colors ${
              isConfirmationValid && !isLoading
                ? "bg-red-500 hover:bg-red-600 cursor-pointer"
                : "bg-gray-300 cursor-not-allowed"
            }`}
          >
            {isLoading ? "Archiving..." : "Archive"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
