import { Copy } from "lucide-react";
import { memo, useState } from "react";
import { useToast } from "../ToastProvider";

type InfoRowProps = {
  title: string;
  value: string;
  copyable?: boolean;
  copyValue?: string; // Optional separate value for copying
};

function InfoRow({ title, value, copyable = false, copyValue }: InfoRowProps) {
  const { showToast } = useToast();
  const [isHovered, setIsHovered] = useState(false);

  const handleCopy = async () => {
    try {
      // Use copyValue if provided, otherwise use display value
      await navigator.clipboard.writeText(copyValue || value);
      showToast("Copied to clipboard");
    } catch (err) {
      console.error("Failed to copy: ", err);
      showToast("Failed to copy");
    }
  };

  const showCopyButton = copyable && isHovered;

  return (
    <div
      className="bg-white border border-gray-200 rounded-[2px] px-2"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="flex justify-between items-center">
        <span className="text-xs font-medium text-gray-700 py-2">{title}</span>
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-900 py-2">{value}</span>
          {showCopyButton && (
            <button
              onClick={handleCopy}
              className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer h-5 w-5 rounded-[2px] flex items-center justify-center ml-1"
              title="Copy to clipboard"
            >
              <Copy size={12} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default memo(InfoRow);
