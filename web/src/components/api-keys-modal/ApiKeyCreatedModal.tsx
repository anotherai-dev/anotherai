import { Copy } from "lucide-react";
import { CompleteAPIKey } from "@/types/models";
import { Modal } from "../Modal";
import { useToast } from "../ToastProvider";

interface ApiKeyCreatedModalProps {
  isOpen: boolean;
  onClose: () => void;
  apiKey: CompleteAPIKey | null;
}

export function ApiKeyCreatedModal({ isOpen, onClose, apiKey }: ApiKeyCreatedModalProps) {
  const { showToast } = useToast();

  const handleCopy = async () => {
    if (!apiKey?.key) return;

    try {
      await navigator.clipboard.writeText(apiKey.key);
      showToast("API key copied to clipboard!");
    } catch (error) {
      console.error("Failed to copy API key:", error);
    }
  };

  if (!apiKey) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <div className="flex flex-col w-[500px] max-w-[80vw] bg-white rounded-[2px] border border-gray-200 shadow-lg py-4">
        <h3 className="text-base font-bold text-gray-900 mb-4 border-b border-gray-200 border-dashed pb-4 px-4">
          Save Your Key
        </h3>

        <div className="text-[13px] text-gray-600 mb-4 px-4 pt-1 border-b border-gray-100 pb-3">
          <p className="mb-4">
            Please save this API key somewhere safe and accessible. For security reasons, you will not be able to view
            it again. If you lose this API key, you will need to generate a new one.
          </p>

          <div>
            <div className="flex items-center gap-2 pb-2">
              <code className="flex-1 text-[13px] font-mono bg-white px-3 py-2 rounded border border-gray-200 text-gray-900 break-all">
                {apiKey.key}
              </code>
              <button
                onClick={handleCopy}
                className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer h-9 w-9 rounded-[2px] flex items-center justify-center shadow-sm shadow-black/5"
              >
                <Copy size={14} />
              </button>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 px-4">
          <button
            onClick={onClose}
            className="bg-white border border-gray-200 text-gray-900 font-semibold hover:bg-gray-100 cursor-pointer px-3 py-1.5 rounded-[2px] shadow-sm shadow-black/5 text-[13px]"
          >
            Done
          </button>
        </div>
      </div>
    </Modal>
  );
}
