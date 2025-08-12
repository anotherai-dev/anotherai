import { Plus, X } from "lucide-react";
import { useState } from "react";
import { useOrFetchAPIKeys } from "@/store/apiKeys";
import { CompleteAPIKey } from "@/types/models";
import { LoadingIndicator } from "../LoadingIndicator";
import { ApiKeyCreateModal } from "./ApiKeyCreateModal";
import { ApiKeyCreatedModal } from "./ApiKeyCreatedModal";
import { ApiKeysList } from "./ApiKeysList";

interface ApiKeysModalContentProps {
  onClose: () => void;
}

export function ApiKeysModalContent({ onClose }: ApiKeysModalContentProps) {
  const { apiKeys, isLoading, error } = useOrFetchAPIKeys();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showCreatedModal, setShowCreatedModal] = useState(false);
  const [createdApiKey, setCreatedApiKey] = useState<CompleteAPIKey | null>(
    null
  );

  const handleCreateSuccess = (apiKey: CompleteAPIKey) => {
    setCreatedApiKey(apiKey);
    setShowCreateModal(false);
    setShowCreatedModal(true);
  };

  return (
    <div className="flex flex-col w-[80vw] h-[80vh] max-w-4xl max-h-4xl bg-slate-50 rounded-[2px] border border-gray-200 shadow-lg shadow-black/20">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 border-dashed">
        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer px-2 py-1 rounded-[2px] w-8 h-8 flex items-center justify-center shadow-sm shadow-black/5"
          >
            <X size={16} />
          </button>
          <h2 className="text-base font-bold">Manage API Keys</h2>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer px-3 py-1 rounded-[2px] flex items-center gap-1 shadow-sm shadow-black/5 text-xs font-bold h-8"
        >
          <Plus size={14} />
          New API Key
        </button>
      </div>

      <div className="flex flex-1 w-full overflow-hidden">
        {isLoading ? (
          <div className="flex w-full h-full items-center justify-center">
            <LoadingIndicator />
          </div>
        ) : error ? (
          <div className="flex w-full h-full items-center justify-center">
            <div className="text-center">
              <p className="text-red-600 mb-2">Error loading API keys</p>
              <p className="text-sm text-gray-500">{error.message}</p>
            </div>
          </div>
        ) : (
          <ApiKeysList apiKeys={apiKeys} />
        )}
      </div>

      <ApiKeyCreateModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={handleCreateSuccess}
      />

      <ApiKeyCreatedModal
        isOpen={showCreatedModal}
        onClose={() => setShowCreatedModal(false)}
        apiKey={createdApiKey}
      />
    </div>
  );
}
