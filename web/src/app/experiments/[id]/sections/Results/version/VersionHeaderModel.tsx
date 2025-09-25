import { Plus } from "lucide-react";
import { memo, useState } from "react";
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

function VersionHeaderModel(props: VersionHeaderModelProps) {
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
            <ModelIconWithName
              modelId={version.model}
              size={12}
              nameClassName="text-xs text-gray-900 font-medium"
              reasoningEffort={version.reasoning_effort}
              reasoningBudget={version.reasoning_budget}
            />
          </div>
        </HoverPopover>
      ) : (
        <div
          className="px-2 py-1 text-xs rounded font-medium bg-gray-200 border border-gray-300 text-gray-900 w-fit hover:bg-gray-300 cursor-pointer transition-colors"
          onClick={(e) => handleAddAnnotation(e)}
        >
          <ModelIconWithName
            modelId={version.model}
            size={12}
            nameClassName="text-xs text-gray-900 font-medium"
            reasoningEffort={version.reasoning_effort}
            reasoningBudget={version.reasoning_budget}
          />
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

// Helper function to compare Version objects for model-related properties
function areVersionModelsEqual(prev: Version, next: Version): boolean {
  return (
    prev.id === next.id &&
    prev.model === next.model &&
    prev.reasoning_effort === next.reasoning_effort &&
    prev.reasoning_budget === next.reasoning_budget
  );
}

// Helper function to compare Annotation arrays
function areAnnotationsEqual(prev?: Annotation[], next?: Annotation[]): boolean {
  if (prev === next) return true;
  if (!prev || !next) return false;
  if (prev.length !== next.length) return false;

  for (let i = 0; i < prev.length; i++) {
    if (prev[i].id !== next[i].id || prev[i].text !== next[i].text) {
      return false;
    }
  }
  return true;
}

export default memo(VersionHeaderModel, (prevProps, nextProps) => {
  return (
    prevProps.experimentId === nextProps.experimentId &&
    prevProps.completionId === nextProps.completionId &&
    prevProps.index === nextProps.index &&
    areVersionModelsEqual(prevProps.version, nextProps.version) &&
    areAnnotationsEqual(prevProps.annotations, nextProps.annotations)
  );
});
