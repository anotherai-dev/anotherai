import { APIKey } from "@/types/models";
import { Modal } from "../Modal";

interface DeleteApiKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  apiKey: APIKey | null;
  isDeleting: boolean;
}

export function DeleteApiKeyModal({ isOpen, onClose, onConfirm, apiKey, isDeleting }: DeleteApiKeyModalProps) {
  if (!apiKey) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <div className="flex flex-col w-[400px] max-w-[80vw] bg-white rounded-[2px] border border-gray-200 shadow-lg py-4">
        <h3 className="text-base font-bold text-gray-900 mb-4 border-b border-gray-200 border-dashed pb-4 px-4">
          Delete API Key
        </h3>

        <div className="text-[13px] text-gray-600 mb-4 px-4 border-b border-gray-100 pb-4">
          <p>
            Are you sure you want to delete the API key{" "}
            <span className="font-semibold text-gray-900">{apiKey.name}</span>?
          </p>
          <p>This action cannot be undone.</p>
        </div>

        <div className="flex w-full justify-end gap-2 px-4">
          <button
            onClick={onClose}
            className="bg-white border border-gray-200 text-gray-900 font-semibold hover:bg-gray-100 cursor-pointer px-2.5 py-1.5 rounded-[2px] shadow-sm shadow-black/5 text-[13px]"
            disabled={isDeleting}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="bg-red-600 border border-red-600 text-white font-semibold hover:bg-red-700 cursor-pointer px-2.5 py-1.5 rounded-[2px] shadow-sm shadow-black/5 text-[13px] disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isDeleting}
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
