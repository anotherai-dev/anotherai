import { Copy } from "lucide-react";
import Link from "next/link";
import { memo, useState } from "react";
import { useToast } from "../ToastProvider";

type InfoRowProps = {
  title: string;
  value: string;
  copyable?: boolean;
  copyValue?: string; // Optional separate value for copying
  linkTo?: string; // Optional URL to make the value clickable
  onClick?: () => void; // Optional click handler
};

function InfoRow({ title, value, copyable = false, copyValue, linkTo, onClick }: InfoRowProps) {
  const { showToast } = useToast();
  const [isHovered, setIsHovered] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent triggering the row's onClick
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

  const content = (
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
  );

  if (linkTo) {
    return (
      <Link
        href={linkTo}
        className="block bg-white border border-gray-200 rounded-[2px] px-2 hover:bg-gray-50 cursor-pointer"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {content}
      </Link>
    );
  }

  return (
    <div
      className={`bg-white border border-gray-200 rounded-[2px] px-2 ${onClick ? "cursor-pointer hover:bg-gray-50" : ""}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
    >
      {content}
    </div>
  );
}

export default memo(InfoRow);
