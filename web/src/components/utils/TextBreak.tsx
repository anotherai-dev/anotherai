import { cx } from "class-variance-authority";
import React from "react";

interface TextBreakProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * A utility component that applies intelligent text breaking for long text content.
 * Uses break-words to prefer word-level breaking, falling back to character-level
 * breaking only when necessary for very long words/URLs that would overflow containers.
 * Also uses hyphens-auto for improved readability where possible.
 */
export function TextBreak({ children, className }: TextBreakProps) {
  return <div className={cx("break-words hyphens-auto", className)}>{children}</div>;
}
