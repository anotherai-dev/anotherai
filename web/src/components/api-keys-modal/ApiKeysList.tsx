import { Trash2 } from "lucide-react";
import { useCallback, useState } from "react";
import { SimpleTableComponent } from "@/components/SimpleTableComponent";
import { useToast } from "@/components/ToastProvider";
import { useAPIKeys } from "@/store/apiKeys";
import { APIKey } from "@/types/models";
import { DeleteApiKeyModal } from "./DeleteApiKeyModal";

interface ApiKeysListProps {
  apiKeys: APIKey[];
}

export function ApiKeysList({ apiKeys }: ApiKeysListProps) {
  const { deleteAPIKey } = useAPIKeys();
  const { showToast } = useToast();
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [apiKeyToDelete, setApiKeyToDelete] = useState<APIKey | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteKey = useCallback((apiKey: APIKey) => {
    setApiKeyToDelete(apiKey);
    setShowDeleteModal(true);
  }, []);

  const handleConfirmDelete = useCallback(async () => {
    if (!apiKeyToDelete) return;

    setIsDeleting(true);
    try {
      await deleteAPIKey(apiKeyToDelete.id);
      showToast("API key deleted successfully!");
      setShowDeleteModal(false);
      setApiKeyToDelete(null);
    } catch (error) {
      console.error("Failed to delete API key:", error);
    } finally {
      setIsDeleting(false);
    }
  }, [apiKeyToDelete, deleteAPIKey, showToast]);

  const handleCancelDelete = useCallback(() => {
    setShowDeleteModal(false);
    setApiKeyToDelete(null);
  }, []);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  if (apiKeys.length === 0) {
    return (
      <div className="flex flex-1 w-full items-center justify-center">
        <div className="text-center px-4">
          <h3 className="text-base font-medium text-gray-900 mb-2">No API keys</h3>
          <p className="text-sm text-gray-500">Create your first API key to start using the API.</p>
        </div>
      </div>
    );
  }

  const columnHeaders = ["Name", "Created on", "Key", ""];

  const tableData = apiKeys.map((apiKey) => [
    <span key="name" className="font-medium text-gray-900">
      {apiKey.name}
    </span>,
    <span key="created-on" className="text-gray-700">
      {formatDate(apiKey.created_at)}
    </span>,
    <code key="key" className="text-xs font-mono bg-gray-100 px-2 py-1 rounded text-gray-700">
      {apiKey.partial_key}
    </code>,
    <button
      key="delete"
      onClick={() => handleDeleteKey(apiKey)}
      className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors cursor-pointer rounded"
      title="Delete API key"
    >
      <Trash2 size={14} />
    </button>,
  ]);

  return (
    <div className="flex flex-col flex-1 w-full p-4 overflow-hidden">
      <SimpleTableComponent
        columnHeaders={columnHeaders}
        data={tableData}
        columnWidths={[undefined, "120px", "150px", "40px"]}
        maxHeight="100%"
        cellVerticalAlign="middle"
        className="text-sm"
      />

      <DeleteApiKeyModal
        isOpen={showDeleteModal}
        onClose={handleCancelDelete}
        onConfirm={handleConfirmDelete}
        apiKey={apiKeyToDelete}
        isDeleting={isDeleting}
      />
    </div>
  );
}
