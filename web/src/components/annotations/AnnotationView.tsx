import { Trash2 } from "lucide-react";
import { useMemo } from "react";
import { Annotation } from "@/types/models";
import { formatRelativeDate } from "../utils/utils";

export type AnnotationViewProps = {
  annotation: Annotation;
  className?: string;
  onDelete?: (annotationId: string) => void;
  keyPathPrefix?: string;
};

export function AnnotationView({ annotation, className = "", onDelete, keyPathPrefix }: AnnotationViewProps) {
  // Extract the keyPath without prefix for display
  const displayKeyPath = useMemo(() => {
    if (!annotation.target?.key_path) return undefined;

    if (!keyPathPrefix) return annotation.target.key_path;

    if (annotation.target.key_path === keyPathPrefix) {
      return undefined; // Hide badge if keyPath exactly matches prefix
    }

    if (annotation.target.key_path.startsWith(keyPathPrefix + ".")) {
      return annotation.target.key_path.slice(keyPathPrefix.length + 1); // Remove prefix + dot
    }

    return annotation.target.key_path; // Show full path if no prefix match
  }, [annotation.target?.key_path, keyPathPrefix]);

  return (
    <div className={`p-2 bg-white group relative ${className}`}>
      {onDelete && (
        <button
          onClick={() => onDelete(annotation.id)}
          className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-50 rounded-sm cursor-pointer"
          title="Delete annotation"
        >
          <Trash2 size={14} className="text-red-500" />
        </button>
      )}
      <div className="flex justify-between items-start mb-1">
        <div className="text-xs flex items-center gap-2">
          <span className="text-gray-700 font-semibold">{annotation.author_name}</span>
          <span className="text-gray-400">{formatRelativeDate(annotation.created_at)}</span>
        </div>
      </div>
      {displayKeyPath && (
        <div className="mb-2">
          <span className="inline-block px-2 py-1 text-xs bg-gray-100 border border-gray-200 text-gray-600 font-medium rounded-[2px] whitespace-nowrap">
            {displayKeyPath}
          </span>
        </div>
      )}
      {annotation.text && <div className="text-xs text-gray-800 whitespace-pre-wrap">{annotation.text}</div>}
      {annotation.metric && (
        <div className="mt-2">
          <div className="inline-flex justify-between items-center px-2 py-1 bg-transparent border border-gray-200 text-gray-700 rounded text-xs">
            <span className="text-gray-600 capitalize">{annotation.metric.name.replace(/_/g, " ")}</span>
            <span className="font-medium ml-2">{annotation.metric.value}</span>
          </div>
        </div>
      )}
    </div>
  );
}
