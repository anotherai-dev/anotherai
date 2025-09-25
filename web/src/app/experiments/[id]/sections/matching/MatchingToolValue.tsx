import { Plus } from "lucide-react";
import { memo, useState } from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { AnnotationsView } from "@/components/annotations/AnnotationsView";
import { Annotation, Tool } from "@/types/models";

type MatchingToolValueProps = {
  tools: Tool[];
  annotations?: Annotation[];
  experimentId?: string;
  completionId?: string;
  keyPath?: string;
  position?:
    | "bottom"
    | "top"
    | "left"
    | "right"
    | "topRight"
    | "topRightAligned"
    | "topLeftAligned"
    | "topRightAlignedNew"
    | "rightOverlap"
    | "bottomLeft";
};

function MatchingToolValue({
  tools,
  annotations,
  experimentId,
  completionId,
  keyPath,
  position = "topRightAligned",
}: MatchingToolValueProps) {
  const [showAddForm, setShowAddForm] = useState(false);

  const handleAddAnnotation = (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    setShowAddForm(!showAddForm);
  };

  const toolsDisplay =
    tools && tools.length > 0 ? (
      <div className="space-y-1">
        {tools.map((tool, index) => (
          <div key={index} className="flex justify-between items-center">
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-gray-700 truncate">{tool.name || `Tool ${index + 1}`}</div>
            </div>
            <span className="text-xs text-gray-500 bg-gray-100 px-1 py-0.5 rounded ml-2 flex-shrink-0">function</span>
          </div>
        ))}
      </div>
    ) : (
      <div className="text-xs text-gray-900 bg-white border border-gray-200 rounded-[2px] px-1.5 py-1 whitespace-nowrap">
        No tools available
      </div>
    );

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
          position={position}
          popoverClassName="bg-white border border-gray-200"
          className="w-full block"
        >
          <div
            className="flex items-center w-full hover:bg-gray-100 hover:cursor-pointer transition-colors min-h-[28px] px-2 py-2"
            onClick={(e) => handleAddAnnotation(e)}
          >
            {toolsDisplay}
          </div>
        </HoverPopover>
      ) : (
        <div
          className="flex items-center w-full hover:bg-gray-100 hover:cursor-pointer transition-colors min-h-[28px] px-2 py-2"
          onClick={(e) => handleAddAnnotation(e)}
        >
          {toolsDisplay}
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

// Helper function to compare Tool arrays
function areToolsEqual(prev: Tool[], next: Tool[]): boolean {
  if (prev === next) return true;
  if (prev.length !== next.length) return false;

  for (let i = 0; i < prev.length; i++) {
    if (prev[i].name !== next[i].name || prev[i].description !== next[i].description) {
      return false;
    }
  }
  return true;
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

export default memo(MatchingToolValue, (prevProps, nextProps) => {
  return (
    areToolsEqual(prevProps.tools, nextProps.tools) &&
    prevProps.experimentId === nextProps.experimentId &&
    prevProps.completionId === nextProps.completionId &&
    prevProps.keyPath === nextProps.keyPath &&
    prevProps.position === nextProps.position &&
    areAnnotationsEqual(prevProps.annotations, nextProps.annotations)
  );
});
