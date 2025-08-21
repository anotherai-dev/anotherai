import { cx } from "class-variance-authority";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

type HoverPopoverProps = {
  children: React.ReactNode;
  content: React.ReactNode;
  className?: string;
  popoverClassName?: string;
  delay?: number;
  position?: "top" | "bottom" | "left" | "right" | "topRight" | "topRightAligned" | "rightOverlap" | "bottomLeft";
};

export function HoverPopover({
  children,
  content,
  className = "",
  popoverClassName = "",
  delay = 0,
  position = "top",
}: HoverPopoverProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [popoverPosition, setPopoverPosition] = useState({ top: 0, left: 0 });
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const triggerRef = useRef<HTMLDivElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  const calculatePosition = useCallback(() => {
    if (!triggerRef.current) return;

    const rect = triggerRef.current.getBoundingClientRect();

    let top = 0;
    let left = 0;

    switch (position) {
      case "top":
        top = rect.top - 8;
        left = rect.left + rect.width / 2;
        break;
      case "bottom":
        top = rect.bottom + 4;
        left = rect.left + rect.width / 2;
        // Adjust minimally if popover would be cut off
        setTimeout(() => {
          if (popoverRef.current) {
            const popoverRect = popoverRef.current.getBoundingClientRect();
            const viewportWidth = window.innerWidth;

            // Calculate where the right edge of the popover would be
            const popoverRightEdge = left + popoverRect.width / 2;

            // Only adjust if it would extend beyond viewport (with small buffer)
            if (popoverRightEdge > viewportWidth - 8) {
              // Shift left just enough to fit
              const overflow = popoverRightEdge - (viewportWidth - 8);
              setPopoverPosition((prev) => ({
                ...prev,
                left: prev.left - overflow,
              }));
            }
          }
        }, 0);
        break;
      case "left":
        top = rect.top + rect.height / 2;
        left = rect.left - 8;
        break;
      case "right":
        top = rect.top + rect.height / 2;
        left = rect.right + 8;
        break;
      case "topRight":
        top = rect.top - 4;
        left = rect.right;
        break;
      case "topRightAligned":
        top = rect.top - 32;
        left = rect.right;
        // Adjust after popover is rendered to align right edges
        setTimeout(() => {
          if (popoverRef.current) {
            const popoverRect = popoverRef.current.getBoundingClientRect();
            setPopoverPosition(() => ({
              top: rect.top - popoverRect.height + 8,
              left: rect.right - popoverRect.width,
            }));
          }
        }, 0);
        break;
      case "rightOverlap":
        top = rect.top;
        left = rect.right - 16; // Overlap by 16px from the right edge
        // Adjust after popover is rendered to align bottom of tooltip with top of content
        setTimeout(() => {
          if (popoverRef.current) {
            const popoverRect = popoverRef.current.getBoundingClientRect();
            setPopoverPosition(() => ({
              top: rect.top - popoverRect.height + 4,
              left: rect.right - 16,
            }));
          }
        }, 0);
        break;
      case "bottomLeft":
        top = rect.bottom + 4;
        left = rect.left;
        break;
    }

    setPopoverPosition({ top, left });
  }, [position]);

  const handleMouseEnter = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true);
      // Recalculate position after popover is rendered and has dimensions
      setTimeout(() => calculatePosition(), 0);
    }, delay);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      setIsVisible(false);
    }, 100);
  };

  useEffect(() => {
    if (isVisible) {
      const handleScroll = () => {
        calculatePosition();
      };

      window.addEventListener("scroll", handleScroll, true);
      window.addEventListener("resize", handleScroll);

      return () => {
        window.removeEventListener("scroll", handleScroll, true);
        window.removeEventListener("resize", handleScroll);
      };
    }
  }, [isVisible, calculatePosition]);

  const popoverContent = isVisible ? (
    <div
      ref={popoverRef}
      className={cx(
        "fixed z-[9999] px-2 py-1 text-xs text-white shadow-lg whitespace-nowrap",
        popoverClassName || "bg-gray-900"
      )}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      style={{
        top: popoverPosition.top,
        left: popoverPosition.left,
        transform:
          position === "top"
            ? "translateX(-50%) translateY(-100%)"
            : position === "bottom"
              ? "translateX(-50%)"
              : position === "left" || position === "right"
                ? "translateY(-50%)"
                : position === "topRight"
                  ? "translateX(-50%) translateY(-100%)"
                  : position === "bottomLeft"
                    ? "translateX(0)"
                    : "translateX(-50%)",
      }}
    >
      {content}
    </div>
  ) : null;

  return (
    <>
      <div
        ref={triggerRef}
        className={cx("relative", className)}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {children}
      </div>

      {typeof document !== "undefined" && popoverContent && createPortal(popoverContent, document.body)}
    </>
  );
}
