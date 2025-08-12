import { cx } from "class-variance-authority";
import { Plus } from "lucide-react";
import React, { useMemo } from "react";
import { Annotation } from "../../types/models";
import { HoverPopover } from "../HoverPopover";

export type HoverContainerProps = {
  children: React.ReactNode;
  keyPath?: string;
  className?: string;
  as?: "div" | "button";
  onClick?: (e: React.MouseEvent) => void;
  annotations?: Annotation[];
  onKeypathSelect?: (keyPath: string) => void;
};

export const HoverContainer = (props: HoverContainerProps) => {
  const {
    children,
    className = "",
    as = "div",
    onClick,
    keyPath,
    annotations,
    onKeypathSelect,
  } = props;

  const handleClick = (e: React.MouseEvent) => {
    if (onKeypathSelect && keyPath && supportHover) {
      e.preventDefault();
      e.stopPropagation();
      onKeypathSelect(keyPath);
      return;
    }

    if (onClick) {
      onClick(e);
    }
  };

  const { supportHover, hoverBadgeText, noHoverBadgeText } = useMemo(() => {
    if (!annotations || !keyPath) {
      return {
        supportHover: false,
        hoverBadgeText: undefined,
        noHoverBadgeText: undefined,
      };
    }

    const matchingAnnotations = annotations.filter(
      (annotation) => annotation.target?.key_path === keyPath
    );

    const annotationCount = matchingAnnotations.length;

    return {
      supportHover: true,
      hoverBadgeText: "Add annotation",
      noHoverBadgeText:
        annotationCount > 0
          ? `${annotationCount} annotation${annotationCount === 1 ? "" : "s"}`
          : undefined,
    };
  }, [annotations, keyPath]);

  const Component = as;

  const content = (
    <Component
      className={cx(
        className,
        supportHover &&
          "hover:bg-gray-100 hover:cursor-pointer transition-colors duration-150",
        supportHover && noHoverBadgeText && "flex items-center gap-2"
      )}
      onClick={handleClick}
    >
      {children}
      {supportHover && noHoverBadgeText && (
        <span className="inline-block px-2 py-1 text-xs bg-gray-100 border border-gray-200 text-gray-600 font-medium rounded-[2px] whitespace-nowrap my-2">
          {noHoverBadgeText}
        </span>
      )}
    </Component>
  );

  if (supportHover && hoverBadgeText) {
    return (
      <HoverPopover
        content={
          <span
            className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-white text-gray-900 font-semibold rounded-[2px] whitespace-nowrap cursor-pointer"
            onClick={handleClick}
          >
            <Plus className="w-3.5 h-3.5" />
            {hoverBadgeText}
          </span>
        }
        position="topRight"
        delay={0}
        popoverClassName="bg-white border border-gray-200"
      >
        {content}
      </HoverPopover>
    );
  }

  return content;
};
