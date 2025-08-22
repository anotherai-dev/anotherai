import { Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { AnnotationsView } from "@/components/annotations/AnnotationsView";
import { Annotation } from "@/types/models";

type MatchingBaseValueProps = {
  value: unknown;
  annotations?: Annotation[];
  experimentId?: string;
  completionId?: string;
  keyPath?: string;
};

export function MatchingBaseValue({ value, annotations, experimentId, completionId, keyPath }: MatchingBaseValueProps) {
  const [showAddForm, setShowAddForm] = useState(false);

  const displayValue = useMemo(() => {
    if (value === null || value === undefined) {
      return "null";
    } else if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      return String(value);
    } else if (Array.isArray(value)) {
      return value.length === 0 ? "No tools available" : JSON.stringify(value);
    } else if (typeof value === "object") {
      return JSON.stringify(value);
    } else {
      return String(value);
    }
  }, [value]);

  const handleAddAnnotation = (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    setShowAddForm(!showAddForm);
  };

  return (
    <>
      {!showAddForm ? (
        <HoverPopover
          content={
            <span
              className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-white text-gray-900 font-semibold rounded-[2px] whitespace-nowrap cursor-pointer"
              onClick={(e) => handleAddAnnotation(e)}
            >
              <Plus className="w-3.5" />
              Add annotation
            </span>
          }
          position="topRightAligned"
          popoverClassName="bg-white border border-gray-200"
          className="w-full block"
        >
          <div
            className="flex items-center w-full hover:bg-gray-100 hover:cursor-pointer transition-colors min-h-[28px] px-2 py-2"
            onClick={(e) => handleAddAnnotation(e)}
          >
            <div className="text-xs text-gray-900 bg-white border border-gray-200 rounded-[2px] px-1.5 py-1 whitespace-nowrap">
              {displayValue}
            </div>
          </div>
        </HoverPopover>
      ) : (
        <div
          className="flex items-center w-full hover:bg-gray-100 hover:cursor-pointer transition-colors min-h-[28px] px-2 py-2"
          onClick={(e) => handleAddAnnotation(e)}
        >
          <div className="text-xs text-gray-900 bg-white border border-gray-200 rounded-[2px] px-1.5 py-1 whitespace-nowrap">
            {displayValue}
          </div>
        </div>
      )}
      <div className="px-2">
        <AnnotationsView
          annotations={annotations}
          keyPathPrefix={keyPath}
          experimentId={experimentId}
          completionId={completionId}
          showAddButton={false}
          showAddForm={showAddForm}
          onAddFormClose={() => setShowAddForm(false)}
        />
      </div>
    </>
  );
}
