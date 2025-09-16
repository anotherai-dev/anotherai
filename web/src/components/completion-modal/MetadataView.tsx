import { useRouter } from "next/navigation";
import { useCallback } from "react";

type InfoRowProps = {
  title: string;
  value: string;
  onClick?: () => void;
};

function InfoRow({ title, value, onClick }: InfoRowProps) {
  return (
    <div
      className={`bg-white border border-gray-200 rounded-[2px] p-2 ${onClick ? "cursor-pointer hover:bg-gray-50 hover:border-gray-300" : ""}`}
      onClick={onClick}
    >
      <div className="flex justify-between items-center">
        <span className="text-xs font-medium text-gray-700">{title}</span>
        <span className="text-xs text-gray-900 text-right">{value}</span>
      </div>
    </div>
  );
}

type Props = {
  metadata: Record<string, unknown>;
};

export function MetadataView({ metadata }: Props) {
  const router = useRouter();

  const handleMetadataClick = useCallback(
    (key: string, value: unknown) => {
      const stringValue = typeof value === "string" ? value : JSON.stringify(value);
      const query = `SELECT * FROM completions WHERE metadata['${key}'] = '${stringValue}'`;
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
