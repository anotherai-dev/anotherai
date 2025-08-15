import { useCallback, useState } from "react";
import { useAPIKeys } from "@/store/apiKeys";
import { CompleteAPIKey } from "@/types/models";
import { Modal } from "../Modal";

interface ApiKeyCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (apiKey: CompleteAPIKey) => void;
}

export function ApiKeyCreateModal({ isOpen, onClose, onSuccess }: ApiKeyCreateModalProps) {
  const [name, setName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const { createAPIKey } = useAPIKeys();

  const handleSubmit = useCallback(async () => {
    if (!name.trim()) return;

    setIsCreating(true);
    try {
      const newApiKey = await createAPIKey({ name: name.trim() });
      if (newApiKey) {
        onSuccess(newApiKey);
        setName("");
        onClose();
      }
    } catch (error) {
      console.error("Failed to create API key:", error);
    } finally {
      setIsCreating(false);
    }
  }, [name, createAPIKey, onSuccess, onClose]);

  const handleClose = () => {
    setName("");
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose}>
      <div className="flex flex-col w-[400px] max-w-[80vw] bg-white rounded-[2px] border border-gray-200 shadow-lg py-4">
        <h3 className="text-base font-bold text-gray-900 mb-4 border-b border-gray-200 border-dashed pb-4 px-4">
          Create New API Key
        </h3>

        <div className="text-[13px] text-gray-600 mb-4 px-4 pt-1 pb-3 border-b border-gray-100">
          <div className="mb-2">
            <label htmlFor="apiKeyName" className="block text-[13px] font-semibold text-gray-700 mb-2">
              API Key Name
            </label>
            <input
              id="apiKeyName"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter a name for your API key"
              className="w-full px-3 py-2 text-[13px] border border-gray-300 rounded-[2px] focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
              disabled={isCreating}
              autoComplete="off"
              spellCheck="false"
              onKeyDown={(e) => {
                if (e.key === "Enter" && name.trim() && !isCreating) {
                  handleSubmit();
                }
              }}
            />
          </div>
        </div>

        <div className="flex w-full justify-end gap-2 px-4">
          <button
            onClick={handleClose}
            className="bg-white border border-gray-200 text-gray-900 font-semibold hover:bg-gray-100 cursor-pointer px-2 py-1.5 rounded-[2px] shadow-sm shadow-black/5 text-[13px]"
            disabled={isCreating}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!name.trim() || isCreating}
            className="bg-blue-600 border border-blue-600 text-white font-semibold hover:bg-blue-700 cursor-pointer px-2 py-1.5 rounded-[2px] shadow-sm shadow-black/5 text-[13px] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isCreating ? "Creating..." : "Create API Key"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
