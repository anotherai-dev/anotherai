import { cx } from "class-variance-authority";
import { ChevronDown, ChevronRight } from "lucide-react";
import React, { useState } from "react";
import { Annotation } from "../../types/models";
import { HoverContainer } from "./HoverContainer";
import { ValueDisplay } from "./ValueDisplay";

export type VariablesViewerProps = {
  variables: Record<string, unknown>;
  className?: string;
  hideBorderForFirstLevel?: boolean;
  textSize?: "xs" | "sm" | "base" | string;
  annotations?: Annotation[];
  onKeypathSelect?: (keyPath: string) => void;
  showSeeMore?: boolean;
  maxHeight?: string;
};

const getTextSizeStyle = (textSize: "xs" | "sm" | "base" | string = "xs") => {
  if (textSize === "xs" || textSize === "sm" || textSize === "base") {
    return {
      className: textSize === "xs" ? "text-xs" : textSize === "sm" ? "text-sm" : "text-base",
      style: {},
    };
  }
  return { className: "", style: { fontSize: textSize } };
};

const renderValueBadge = (
  value: unknown,
  textSize: "xs" | "sm" | "base" | string = "xs",
  showSeeMore: boolean = false
) => {
  return <ValueDisplay value={value} textSize={textSize} showSeeMore={showSeeMore} />;
};

const renderProperty = (
  key: string,
  value: unknown,
  textSize: "xs" | "sm" | "base" | string = "xs",
  annotations?: Annotation[],
  keyPath: string = "",
  onKeypathSelect?: (keyPath: string) => void,
  showSeeMore: boolean = false
): React.ReactElement => {
  // For objects, wrap the whole object and its properties in a rectangle
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const entries = Object.entries(value);
    const shouldHideBorder = false;
    const { className: textSizeClass, style: textSizeStyle } = getTextSizeStyle(textSize);

    if (shouldHideBorder) {
      // Render without border for first level
      return (
        <div key={key} className="mb-3 inline-block">
          <div className="flex items-center gap-3 py-2">
            <span className={cx("font-medium text-gray-900", textSizeClass)} style={textSizeStyle}>
              {key}
            </span>
          </div>

          <div className="bg-transparent">
            {entries.map(([childKey, childValue], index) => {
              const childKeyPath = keyPath ? `${keyPath}.${childKey}` : childKey;
              return (
                <div key={childKey}>
                  {index > 0 && <div className="border-t border-dashed border-gray-200 -mx-px"></div>}
                  <div className="p-1">
                    {renderProperty(
                      childKey,
                      childValue,
                      textSize,
                      annotations,
                      childKeyPath,
                      onKeypathSelect,
                      showSeeMore
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      );
    }

    return (
      <div key={key} className="border border-gray-200 rounded-[2px] mb-3 inline-block">
        <div className="flex items-center gap-3 px-3 py-2 bg-gray-100 rounded-t-[2px] border-b border-gray-200">
          <span className={cx("font-medium text-gray-900", textSizeClass)} style={textSizeStyle}>
            {key}
          </span>
        </div>

        <div className="bg-transparent">
          {entries.map(([childKey, childValue], index) => {
            const childKeyPath = keyPath ? `${keyPath}.${childKey}` : childKey;
            return (
              <div key={childKey}>
                {index > 0 && <div className="border-t border-dashed border-gray-200 -mx-px"></div>}
                <div className="p-1">
                  {renderProperty(
                    childKey,
                    childValue,
                    textSize,
                    annotations,
                    childKeyPath,
                    onKeypathSelect,
                    showSeeMore
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // For arrays, use CollapsibleArray component
  if (Array.isArray(value)) {
    return (
      <CollapsibleArray
        key={key}
        arrayKey={key}
        arrayValue={value}
        textSize={textSize}
        annotations={annotations}
        keyPath={keyPath}
        onKeypathSelect={onKeypathSelect}
        showSeeMore={showSeeMore}
      />
    );
  }

  // For primitive types, display badge below property name
  const isArrayIndex = /^\d+$/.test(key);
  const { className: textSizeClass, style: textSizeStyle } = getTextSizeStyle(textSize);

  return (
    <div key={key} className="py-1">
      <HoverContainer
        keyPath={keyPath}
        className="inline-block px-2 py-1 rounded"
        annotations={annotations}
        onKeypathSelect={onKeypathSelect}
      >
        <div className="mb-1">
          <span
            className={cx("font-semibold", textSizeClass, isArrayIndex ? "text-gray-600" : "text-gray-900")}
            style={textSizeStyle}
          >
            {key}
            {!!key && ":"}
          </span>
        </div>
        <div>{renderValueBadge(value, textSize, showSeeMore)}</div>
      </HoverContainer>
    </div>
  );
};

function CollapsibleArray({
  arrayKey,
  arrayValue,
  textSize = "xs",
  keyPath = "",
  annotations,
  onKeypathSelect,
  showSeeMore = false,
}: {
  arrayKey: string;
  arrayValue: unknown[];
  textSize?: "xs" | "sm" | "base" | string;
  keyPath?: string;
  annotations?: Annotation[];
  onKeypathSelect?: (keyPath: string) => void;
  showSeeMore?: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const { className: textSizeClass, style: textSizeStyle } = getTextSizeStyle(textSize);

  return (
    <div>
      <div className="flex items-center gap-3 py-1">
        <HoverContainer
          keyPath={keyPath}
          className="flex items-center gap-1 font-medium text-gray-900 hover:text-gray-700 px-2 -mx-2 rounded"
          as="button"
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded(!isExpanded);
          }}
          annotations={annotations}
          onKeypathSelect={onKeypathSelect}
        >
          {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          <span className={textSizeClass} style={textSizeStyle}>
            {arrayKey}:
          </span>
        </HoverContainer>
        {!isExpanded && (
          <span
            className={cx(
              "inline-block px-2 py-1 font-medium bg-white border border-gray-200 text-gray-800 rounded-[2px]",
              textSizeClass
            )}
            style={textSizeStyle}
          >
            [{arrayValue.length} items]
          </span>
        )}
      </div>

      {isExpanded && arrayValue.length === 0 ? (
        <span className={cx("text-gray-500 italic font-normal pl-4", textSizeClass)} style={textSizeStyle}>
          empty
        </span>
      ) : isExpanded ? (
        <div className="ml-1 mt-2 relative">
          <div className="ml-3 mt-2">
            {arrayValue.map((item, index) => {
              const isLast = index === arrayValue.length - 1;
              const itemKeyPath = keyPath ? `${keyPath}[${index}]` : `${arrayKey}[${index}]`;
              return (
                <div key={index} className="py-1 relative">
                  {/* Vertical line segment - extends from top to the horizontal connector */}
                  <div className="absolute left-[-10px] top-0 bottom-0 w-px border-l border-gray-200"></div>
                  {/* Horizontal connector from vertical line to item - centered */}
                  <div className="absolute left-[-10px] top-1/2 -translate-y-1/2 w-2 h-px border-t border-gray-200"></div>
                  {/* Hide the vertical line below the last item */}
                  {isLast && <div className="absolute left-[-10px] top-1/2 bottom-0 w-px bg-white"></div>}
                  <div className="flex items-center gap-3">
                    <span className={cx("font-semibold text-gray-600", textSizeClass)} style={textSizeStyle}>
                      {index}:
                    </span>
                    <div className="flex-1">
                      {item && typeof item === "object" && !Array.isArray(item) ? (
                        <div className="border border-gray-200 rounded-[2px] inline-block">
                          <div className="bg-transparent">
                            {Object.entries(item).map(([childKey, childValue], childIndex) => {
                              const childKeyPath = `${itemKeyPath}.${childKey}`;
                              return (
                                <div key={childKey}>
                                  {childIndex > 0 && (
                                    <div className="border-t border-dashed border-gray-200 -mx-px"></div>
                                  )}
                                  <div className="p-1">
                                    {renderProperty(
                                      childKey,
                                      childValue,
                                      textSize,
                                      annotations,
                                      childKeyPath,
                                      onKeypathSelect,
                                      showSeeMore
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ) : (
                        <HoverContainer
                          keyPath={itemKeyPath}
                          className="inline-flex items-center px-2 py-1 rounded"
                          annotations={annotations}
                          onKeypathSelect={onKeypathSelect}
                        >
                          {renderValueBadge(item, textSize, showSeeMore)}
                        </HoverContainer>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function VariablesViewer(props: VariablesViewerProps) {
  const {
    variables,
    className = "",
    hideBorderForFirstLevel = false,
    textSize = "xs",
    annotations,
    onKeypathSelect,
    showSeeMore = true,
    maxHeight = "20rem",
  } = props;

  const { className: textSizeClass, style: textSizeStyle } = getTextSizeStyle(textSize);

  // Convert special height values to CSS
  const getMaxHeightStyle = (height: string) => {
    switch (height) {
      case "full":
        return "100%";
      case "max":
        return "none";
      case "screen":
        return "100vh";
      default:
        return height;
    }
  };

  // Determine if we should show overflow
  const shouldShowOverflow = maxHeight !== "max";

  if (!variables || Object.keys(variables).length === 0) {
    return (
      <div
        className={cx(
          hideBorderForFirstLevel ? "bg-transparent" : "border border-gray-200 rounded-[2px] bg-white",
          className
        )}
      >
        <div className={hideBorderForFirstLevel ? "" : "p-3"}>
          <div className={cx("text-gray-500 italic font-normal", textSizeClass)} style={textSizeStyle}>
            no variables defined
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cx(
        hideBorderForFirstLevel ? "bg-transparent" : "border border-gray-200 rounded-[2px] bg-white",
        className
      )}
    >
      <div
        className={cx(shouldShowOverflow ? "overflow-y-auto" : "", hideBorderForFirstLevel ? "" : "p-3")}
        style={{ maxHeight: getMaxHeightStyle(maxHeight) }}
      >
        <div className="space-y-1">
          {Object.entries(variables).map(([key, value]) =>
            renderProperty(key, value, textSize, annotations, key, onKeypathSelect, showSeeMore)
          )}
        </div>
      </div>
    </div>
  );
}
