import { Plus } from "lucide-react";
import React from "react";
import { useMemo, useState } from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { AnnotationsView } from "@/components/annotations/AnnotationsView";
import { Annotation, Version } from "@/types/models";
import { VersionDifferenceItem } from "./VersionDifferenceItem";

type VersionDifferencesViewProps = {
  version: Version;
  differingKeys: string[];
  annotations?: Annotation[];
  experimentId?: string;
  completionId?: string;
  index?: number;
};

export function VersionDifferencesView(props: VersionDifferencesViewProps) {
  const { version, differingKeys, annotations, experimentId, completionId, index } = props;
  const [showAddForm, setShowAddForm] = useState<string | null>(null);
  console.log("version", version);

  const handleAddAnnotation = (key: string) => (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    setShowAddForm(showAddForm === key ? null : key);
  };

  const keysAndValuesToShow = useMemo(() => {
    return differingKeys
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
        if (typeof value === "object" && Object.keys(value).length === 0) return false;
        return true;
      });
  }, [version, differingKeys]);

  console.log("keysAndValuesToShow", keysAndValuesToShow);

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
                popoverClassName="bg-white border border-gray-200"
                className="w-full block"
              >
                <VersionDifferenceItem keyName={key} value={value} onClick={handleAddAnnotation(key)} />
              </HoverPopover>
            ) : (
              <VersionDifferenceItem keyName={key} value={value} onClick={handleAddAnnotation(key)} />
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
