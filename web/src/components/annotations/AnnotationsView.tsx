import { Plus } from "lucide-react";
import { Info } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { Annotation } from "@/types/models";
import { useAnnotationActions } from "../../store/annotations";
import { HoverPopover } from "../HoverPopover";
import { ImproveAgentAnnotationsInstructionsContent } from "../experiment/ImproveAgentAnnotationsInstructionsContent";
import { AnnotationFilters, filterAnnotations } from "../utils/utils";
import { AddAnnotationForm } from "./AddAnnotationForm";
import { AnnotationView } from "./AnnotationView";
import { AnnotationsPromptLabel } from "./AnnotationsPromptLabel";

export type AnnotationsViewProps = {
  annotations?: Annotation[];
  className?: string;
  showAddButton?: boolean;
  alwaysShowAddForm?: boolean;
  keypathSelected?: string | null;
  setKeypathSelected?: (keyPath: string | null) => void;
  showAddForm?: boolean;
  onAddFormClose?: () => void;
  agentId?: string;
} & AnnotationFilters;

export function AnnotationsView({
  annotations,
  className = "",
  showAddButton = false,
  alwaysShowAddForm = false,
  completionId,
  experimentId,
  keyPath,
  keyPathPrefix,
  keypathSelected,
  setKeypathSelected,
  showAddForm = false,
  onAddFormClose,
  agentId,
}: AnnotationsViewProps) {
  const { deleteAnnotation } = useAnnotationActions();
  const [isAdding, setIsAdding] = useState(false);

  // Filter annotations using the utility function
  const filteredAnnotations = useMemo(() => {
    return filterAnnotations(annotations, {
      completionId,
      keyPath,
      keyPathPrefix,
    });
  }, [annotations, completionId, keyPath, keyPathPrefix]);

  const handleAddAnnotation = () => {
    setIsAdding(true);
  };

  const handleFormCancel = () => {
    setIsAdding(false);
    setKeypathSelected?.(null);
    onAddFormClose?.();
  };

  const handleFormSuccess = () => {
    setIsAdding(false);
    setKeypathSelected?.(null);
    onAddFormClose?.();
  };

  const handleDelete = useCallback(
    async (annotationId: string) => {
      await deleteAnnotation(annotationId);
    },
    [deleteAnnotation]
  );

  // Show component even if no annotations when add button is enabled or form is always shown
  if (filteredAnnotations.length === 0 && !showAddButton && !alwaysShowAddForm && !showAddForm) {
    return null;
  }

  return (
    <div className={className}>
      {filteredAnnotations.length > 0 && (
        <div className="border border-gray-200 rounded-[2px] mb-2 divide-y divide-gray-200">
          {filteredAnnotations.map((annotation) => (
            <AnnotationView
              key={annotation.id}
              annotation={annotation}
              onDelete={handleDelete}
              keyPathPrefix={keyPathPrefix}
            />
          ))}
        </div>
      )}

      {showAddButton && !isAdding && !alwaysShowAddForm && (
        <div className="mb-2 flex flex-row justify-between items-center w-full">
          <div className="flex flex-row">
            <button
              onClick={handleAddAnnotation}
              className="text-xs px-2 py-1 bg-transparent border border-indigo-200 text-indigo-700 rounded-l-sm transition-colors flex items-center gap-1 cursor-pointer hover:bg-indigo-50 flex-shrink-0"
              title="Add annotation"
            >
              <Plus size={12} />
              Add Annotation
            </button>
            {agentId && (
              <HoverPopover
                content={<ImproveAgentAnnotationsInstructionsContent agentId={agentId} experimentId={experimentId} />}
                position="bottom"
                popoverClassName="bg-gray-900 text-white rounded-[4px]"
                className=""
              >
                <button
                  className=" flex h-full text-xs px-1.5 py-1 bg-transparent border-l-0 border border-indigo-200 text-indigo-700 rounded-r-sm transition-colors items-center gap-1 cursor-pointer hover:bg-indigo-50 flex-shrink-0"
                  title="Annotation prompt"
                >
                  <Info size={12} />
                </button>
              </HoverPopover>
            )}
          </div>

          {agentId && <AnnotationsPromptLabel annotations={filteredAnnotations} agentId={agentId} experimentId={experimentId} />}
        </div>
      )}

      {/* Add annotation form */}
      {(isAdding || keypathSelected || alwaysShowAddForm || showAddForm) && (
        <div className="mb-2">
          <AddAnnotationForm
            completionId={completionId}
            experimentId={experimentId}
            keyPath={keypathSelected ?? keyPath}
            keyPathPrefix={keyPathPrefix}
            onCancel={handleFormCancel}
            onSuccess={handleFormSuccess}
          />
        </div>
      )}
    </div>
  );
}
