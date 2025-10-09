import { Copy } from "lucide-react";
import { useRouter } from "next/navigation";
import { memo, useCallback, useState } from "react";
import { useCopy } from "../../hooks/useCopy";
import { buildQuery } from "../../utils/queries";

type InfoRowProps = {
  title: string;
  value: string;
  onClick?: () => void;
};

const InfoRow = memo(function InfoRow({ title, value, onClick }: InfoRowProps) {
  const { copyToClipboard } = useCopy();
  const [isHovered, setIsHovered] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent triggering the onClick for deeplink
    await copyToClipboard(value);
  };

  const showCopyButton = isHovered;

  return (
    <div
      className={`bg-white border border-gray-200 rounded-[2px] ${isHovered ? "px-2 py-1.5" : "p-2"} ${onClick ? "cursor-pointer hover:bg-gray-50 hover:border-gray-200" : ""}`}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="flex justify-between items-center">
        <span className="text-xs font-medium text-gray-700">{title}</span>
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-900 text-right">{value}</span>
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
});

type Props = {
  metadata: Record<string, unknown>;
};

function MetadataView({ metadata }: Props) {
  const router = useRouter();

  const handleMetadataClick = useCallback(
    (key: string, value: unknown) => {
      const stringValue = typeof value === "string" ? value : JSON.stringify(value);
      const whereClause = `metadata['${key}'] = '${stringValue}'`;
      const query = buildQuery(whereClause);
      const encodedQuery = encodeURIComponent(query);
      router.push(`/completions?newQuery=${encodedQuery}`);
    },
    [router]
  );

  if (!metadata || Object.keys(metadata).length === 0) {
    return null;
  }

  return (
    <div className="mt-4 py-4 border-t border-gray-200 border-dashed px-4">
      <div className="text-xs font-medium text-gray-400 mb-2">Metadata</div>
      <div className="space-y-2">
        {Object.entries(metadata).map(([key, value]) => (
          <InfoRow
            key={key}
            title={key}
            value={typeof value === "string" ? value : JSON.stringify(value)}
            onClick={() => handleMetadataClick(key, value)}
          />
        ))}
      </div>
    </div>
  );
}

// Helper function to shallow compare metadata objects
function areMetadataObjectsEqual(prev: Record<string, unknown>, next: Record<string, unknown>): boolean {
  const prevKeys = Object.keys(prev);
  const nextKeys = Object.keys(next);

  if (prevKeys.length !== nextKeys.length) {
    return false;
  }

  for (const key of prevKeys) {
    if (prev[key] !== next[key]) {
      return false;
    }
  }

  return true;
}

export default memo(MetadataView, (prevProps, nextProps) => {
  return areMetadataObjectsEqual(prevProps.metadata, nextProps.metadata);
});
