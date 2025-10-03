import { useRouter } from "next/navigation";
import { memo, useCallback } from "react";
import { buildQuery } from "../../utils/queries";
import InfoRow from "./InfoRow";

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
            copyable={true}
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
