import { Plus } from "lucide-react";
import { useState } from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { ModelIconWithName } from "@/components/ModelIcon";
import { AnnotationsView } from "@/components/annotations/AnnotationsView";
import { Annotation, Version } from "@/types/models";

type VersionHeaderModelProps = {
  version: Version;
  annotations?: Annotation[];
  experimentId?: string;
  completionId?: string;
  index?: number;
};

export function VersionHeaderModel(props: VersionHeaderModelProps) {
  const { version, annotations, experimentId, completionId, index } = props;
  const [showAddForm, setShowAddForm] = useState(false);

  const keyPath = index !== undefined ? `versions.${index}.model` : "model";

  const handleAddAnnotation = (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    setShowAddForm(!showAddForm);
  };

  return (
    <div className="space-y-2">
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
          position="rightOverlap"
          popoverClassName="bg-white border border-gray-200"
        >
          <div
            className="px-2 py-1 text-xs rounded font-medium bg-gray-200 border border-gray-300 text-gray-900 w-fit hover:bg-gray-300 cursor-pointer transition-colors"
            onClick={(e) => handleAddAnnotation(e)}
          >
            <ModelIconWithName modelId={version.model} size={12} nameClassName="text-xs text-gray-900 font-medium" />
          </div>
        </HoverPopover>
      ) : (
        <div
          className="px-2 py-1 text-xs rounded font-medium bg-gray-200 border border-gray-300 text-gray-900 w-fit hover:bg-gray-300 cursor-pointer transition-colors"
          onClick={(e) => handleAddAnnotation(e)}
        >
          <ModelIconWithName modelId={version.model} size={12} nameClassName="text-xs text-gray-900 font-medium" />
        </div>
      )}
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
  );
}
