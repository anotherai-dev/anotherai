import { X } from "lucide-react";
import { useState } from "react";
import { Modal } from "@/components/Modal";
import { SchemaViewer } from "@/components/SchemaViewer";
import { OutputSchema, Tool } from "@/types/models";

interface ToolEntryProps {
  tool: Tool;
  index: number;
  showSeparator: boolean;
}

export function ToolEntry({ tool, index, showSeparator }: ToolEntryProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleClick = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  // Convert tool input_schema to OutputSchema format for SchemaViewer
  const inputSchemaAsOutputSchema: OutputSchema = {
    id: `${tool.name}-input-schema`,
    json_schema: tool.input_schema,
  };

  return (
    <>
      <div>
        <div
          className="flex justify-between items-center cursor-pointer hover:bg-gray-50 transition-colors rounded-[2px] p-1 -m-1"
          onClick={handleClick}
        >
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-gray-700 truncate">{tool.name || `Tool ${index + 1}`}</div>
            {tool.description && <div className="text-xs text-gray-500 truncate mt-0.5">{tool.description}</div>}
          </div>
          <span className="text-xs text-gray-500 bg-gray-100 px-1.5 py-1 rounded-[2px] ml-2 flex-shrink-0">
            function
          </span>
        </div>
        {showSeparator && <div className="border-t border-gray-100 mt-2"></div>}
      </div>

      <Modal isOpen={isModalOpen} onClose={handleCloseModal}>
        <div className="bg-white rounded-[2px] border border-gray-200 shadow-lg max-w-2xl mx-auto">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 border-dashed">
            <div className="flex items-center gap-3">
              <button
                onClick={handleCloseModal}
                className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer px-2 py-1 rounded-[2px] w-8 h-8 flex items-center justify-center shadow-sm shadow-black/5"
              >
                <X size={16} />
              </button>
              <h3 className="text-base font-bold text-gray-900">{tool.name || `Tool ${index + 1}`}</h3>
            </div>
          </div>
          {tool.description && (
            <div className="text-[13px] text-gray-600 px-4 pt-4 pb-3">
              <p>{tool.description}</p>
            </div>
          )}
          <div className="px-4 pb-4">
            <h4 className="text-[13px] font-semibold text-gray-900 mb-2 mt-1">Input Schema</h4>
            <SchemaViewer schema={inputSchemaAsOutputSchema} showDescriptions={true} />
          </div>
        </div>
      </Modal>
    </>
  );
}
