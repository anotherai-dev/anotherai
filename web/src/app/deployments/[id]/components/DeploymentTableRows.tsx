import { Copy } from "lucide-react";
import { useCallback } from "react";
import { useToast } from "@/components/ToastProvider";

interface TableRow {
  label: string;
  value: React.ReactNode;
  copyValue?: string;
  copyLabel?: string;
}

interface DeploymentTableRowsProps {
  rows: TableRow[];
  isLast?: boolean;
}

export function DeploymentTableRows({ rows, isLast = false }: DeploymentTableRowsProps) {
  const { showToast } = useToast();

  const handleCopy = useCallback(
    async (copyValue: string, copyLabel: string) => {
      try {
        await navigator.clipboard.writeText(copyValue);
        showToast(`${copyLabel} copied to clipboard`);
      } catch (err) {
        console.error("Failed to copy: ", err);
        showToast(`Failed to copy ${copyLabel}`);
      }
    },
    [showToast]
  );

  return (
    <>
      {rows.map((row, index) => {
        const isPromptOrSchema = row.label === "Prompt" || row.label === "Output Schema";

        return (
          <div
            key={row.label}
            className={`flex ${!isLast || index < rows.length - 1 ? "border-b border-gray-100" : ""}`}
          >
            <div
              className={`w-[250px] px-4 py-3 text-[13px] font-medium text-gray-700 border-r border-gray-100 flex ${isPromptOrSchema ? "items-start" : "items-center"}`}
            >
              {row.label}
            </div>
            <div className="flex-1 px-4 py-3 text-[13px] text-gray-700">
              {isPromptOrSchema ? (
                row.value
              ) : row.copyValue ? (
                <div className="group flex items-center gap-1">
                  <div className="bg-white border border-gray-200 rounded-[2px] px-2 py-1 w-fit cursor-pointer">
                    <span className="text-xs text-gray-900">{row.value}</span>
                  </div>
                  <div className="bg-white border border-gray-200 rounded-[2px] w-7 h-7 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all">
                    <button
                      onClick={() => row.copyValue && row.copyLabel && handleCopy(row.copyValue, row.copyLabel)}
                      className="text-gray-500 hover:text-gray-700 transition-colors cursor-pointer"
                      title={`Copy ${row.copyLabel}`}
                    >
                      <Copy size={12} />
                    </button>
                  </div>
                </div>
              ) : (
                <div className="bg-white border border-gray-200 rounded-[2px] px-2 py-1 w-fit">{row.value}</div>
              )}
            </div>
          </div>
        );
      })}
    </>
  );
}
