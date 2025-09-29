import { cx } from "class-variance-authority";
import { Copy } from "lucide-react";
import React, { memo, useCallback, useEffect, useRef, useState } from "react";
import { TextBreak } from "@/components/utils/TextBreak";
import { useToast } from "../ToastProvider";
import { ImageViewer } from "../messages/ImageViewer";

const MAX_VALUE_LENGTH = 1500;
const MAX_HEIGHT_PX = 150;

// Helper function to detect image data URIs
const isImageDataUri = (value: string): boolean => {
  return typeof value === "string" && value.startsWith("data:image/");
};

// Helper function to detect image URLs
const isImageUrl = (value: string): boolean => {
  if (typeof value !== "string") return false;

  const imageExtensions = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tiff"];
  const lowercaseValue = value.toLowerCase();

  // Check if it's a URL and ends with an image extension
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return imageExtensions.some((ext) => lowercaseValue.includes(ext));
  }

  return false;
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

export type ValueDisplayProps = {
  value: unknown;
  textSize: "xs" | "sm" | "base" | string;
  showSeeMore: boolean;
};

function ValueDisplay({ value, textSize, showSeeMore }: ValueDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [shouldTruncateByHeight, setShouldTruncateByHeight] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const contentRef = useRef<HTMLSpanElement>(null);
  const { className: textSizeClass, style: textSizeStyle } = getTextSizeStyle(textSize);
  const { showToast } = useToast();

  const copyToClipboard = useCallback(async () => {
    const textToCopy = typeof value === "string" ? value : String(value);
    try {
      await navigator.clipboard.writeText(textToCopy);
      showToast("Copied to clipboard");
    } catch (err) {
      console.error("Failed to copy to clipboard:", err);
      showToast("Failed to copy");
    }
  }, [value, showToast]);

  // Check height-based truncation - must be at top level
  useEffect(() => {
    if (contentRef.current && !isExpanded && showSeeMore && typeof value === "string") {
      // Use requestAnimationFrame to ensure layout is complete after break-all wrapping
      requestAnimationFrame(() => {
        if (contentRef.current) {
          const height = contentRef.current.scrollHeight;
          setShouldTruncateByHeight(height > MAX_HEIGHT_PX);
        }
      });
    }
  }, [value, isExpanded, showSeeMore]);

  // Handle string values with potential see more functionality
  if (typeof value === "string") {
    // Special handling for image data URIs
    if (isImageDataUri(value)) {
      return (
        <div
          className={cx("inline-block p-3 bg-white border border-gray-200 rounded-[2px] relative", textSizeClass)}
          style={textSizeStyle}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          <div className="mb-2">
            <ImageViewer imageUrl={value} alt="Variable image" />
          </div>
          <div className="text-xs text-gray-500">Image data URI ({Math.round(value.length / 1024)}KB)</div>
          {isHovered && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                copyToClipboard();
              }}
              className="absolute top-1 right-1 p-1 bg-white border border-gray-200 rounded-[2px] hover:bg-gray-100 transition-colors cursor-pointer"
              title="Copy image data URI to clipboard"
            >
              <Copy size={12} />
            </button>
          )}
        </div>
      );
    }

    // Special handling for image URLs
    if (isImageUrl(value)) {
      return (
        <div
          className={cx("inline-block relative", textSizeClass)}
          style={textSizeStyle}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          <ImageViewer imageUrl={value} alt="Variable image" />
          {isHovered && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                copyToClipboard();
              }}
              className="absolute top-1 right-1 p-1 bg-white border border-gray-200 rounded-[2px] hover:bg-gray-100 transition-colors cursor-pointer"
              title="Copy image URL to clipboard"
            >
              <Copy size={12} />
            </button>
          )}
        </div>
      );
    }

    // Regular string handling
    const shouldTruncateByLength = showSeeMore && value.length > MAX_VALUE_LENGTH;
    const shouldTruncate = shouldTruncateByLength || shouldTruncateByHeight;
    const displayValue = shouldTruncateByLength && !isExpanded ? value.slice(0, MAX_VALUE_LENGTH) : value;

    return (
      <span
        ref={contentRef}
        className={cx(
          "inline-block px-3 py-1.5 font-medium bg-white border border-gray-200 text-gray-800 rounded-[2px] relative break-all hyphens-auto",
          textSizeClass
        )}
        style={textSizeStyle}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div
          className={cx("py-1 break-all hyphens-auto", shouldTruncateByHeight && !isExpanded ? "overflow-hidden" : "")}
          style={shouldTruncateByHeight && !isExpanded ? { maxHeight: `${MAX_HEIGHT_PX - 30}px` } : {}}
        >
          {'"'}
          {displayValue}
          {shouldTruncateByLength && !isExpanded && "..."}
          {'"'}
        </div>
        {shouldTruncate && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className="py-1.5 text-xs text-blue-600 hover:text-blue-800 font-bold cursor-pointer"
          >
            {isExpanded ? "See Less" : "See More"}
          </button>
        )}
        {isHovered && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              copyToClipboard();
            }}
            className="absolute top-1 right-1 p-1 bg-white border border-gray-200 rounded-[2px] hover:bg-gray-100 transition-colors cursor-pointer"
            title="Copy to clipboard"
          >
            <Copy size={12} />
          </button>
        )}
      </span>
    );
  }

  // Handle other value types normally
  const displayValue =
    value === null
      ? "null"
      : value === undefined
        ? "undefined"
        : Array.isArray(value)
          ? `[${value.length} items]`
          : typeof value === "object"
            ? "{object}"
            : String(value);

  return (
    <span
      className={cx(
        "inline-block px-3 py-1.5 font-medium bg-white border border-gray-200 text-gray-800 rounded-[2px] relative",
        textSizeClass
      )}
      style={textSizeStyle}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <TextBreak>{displayValue}</TextBreak>
      {isHovered && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            copyToClipboard();
          }}
          className="absolute top-1 right-1 p-1 bg-white border border-gray-200 rounded-[2px] hover:bg-gray-100 transition-colors cursor-pointer"
          title="Copy to clipboard"
        >
          <Copy size={12} />
        </button>
      )}
    </span>
  );
}

export default memo(ValueDisplay, (prevProps, nextProps) => {
  return (
    prevProps.value === nextProps.value &&
    prevProps.textSize === nextProps.textSize &&
    prevProps.showSeeMore === nextProps.showSeeMore
  );
});
