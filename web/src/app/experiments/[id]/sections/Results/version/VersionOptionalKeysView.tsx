import { Plus } from "lucide-react";
import React from "react";
import { useMemo, useState } from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { AnnotationsView } from "@/components/annotations/AnnotationsView";
import { Annotation, Version } from "@/types/models";

type VersionOptionalKeysViewProps = {
  version: Version;
  optionalKeysToShow: string[];
  annotations?: Annotation[];
  experimentId?: string;
  completionId?: string;
  index?: number;
};

export function VersionOptionalKeysView(props: VersionOptionalKeysViewProps) {
  const {
    version,
    optionalKeysToShow,
    annotations,
    experimentId,
    completionId,
    index,
  } = props;
  const [showAddForm, setShowAddForm] = useState<string | null>(null);

  const handleAddAnnotation = (key: string) => (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    setShowAddForm(showAddForm === key ? null : key);
  };

  const keysAndValuesToShow = useMemo(() => {
    return optionalKeysToShow
      .map((key) => {
        const value = version[key as keyof Version];
        return {
          key,
          value,
        };
      })
      .filter(({ value }) => {
        // Filter out empty values
        if (value === null || value === undefined) return false;
        if (typeof value === "string" && value.trim() === "") return false;
        if (Array.isArray(value) && value.length === 0) return false;
        if (typeof value === "object" && Object.keys(value).length === 0)
          return false;
        return true;
      });
  }, [version, optionalKeysToShow]);

  if (keysAndValuesToShow.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <div className="mt-3 pt-2 border-t border-gray-200" />
      {keysAndValuesToShow.map(({ key, value }) => {
        const keyPath = index !== undefined ? `versions.${index}.${key}` : key;
        const isShowingForm = showAddForm === key;

        return (
          <React.Fragment key={key}>
            {!isShowingForm ? (
              <HoverPopover
                content={
                  <span
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-white text-gray-900 font-semibold rounded-[2px] whitespace-nowrap cursor-pointer"
                    onClick={handleAddAnnotation(key)}
                  >
                    <Plus className="w-3.5" />
                    Add annotation
                  </span>
                }
                position="rightOverlap"
                delay={0}
                popoverClassName="bg-white border border-gray-200"
                className="w-full block"
              >
                <div
                  className="flex items-center justify-between px-2 py-1 text-xs rounded font-medium bg-gray-100 border border-gray-200 text-gray-700 w-full hover:bg-gray-200 cursor-pointer transition-colors"
                  onClick={handleAddAnnotation(key)}
                >
                  <span className="text-gray-500 capitalize">{key}</span>
                  <span className="font-semibold">{String(value)}</span>
                </div>
              </HoverPopover>
            ) : (
              <div
                className="flex items-center justify-between px-2 py-1 text-xs rounded font-medium bg-gray-100 border border-gray-200 text-gray-700 w-full hover:bg-gray-200 cursor-pointer transition-colors"
                onClick={handleAddAnnotation(key)}
              >
                <span className="text-gray-500 capitalize">{key}</span>
                <span className="font-semibold">{String(value)}</span>
              </div>
            )}
            <AnnotationsView
              annotations={annotations}
              keyPathPrefix={keyPath}
              experimentId={experimentId}
              completionId={completionId}
              showAddButton={false}
              showAddForm={isShowingForm}
              onAddFormClose={() => setShowAddForm(null)}
            />
          </React.Fragment>
        );
      })}
    </div>
  );
}
