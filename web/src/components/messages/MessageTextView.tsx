import React, { useEffect, useRef, useState } from "react";

// Configuration
const MAX_TEXT_LENGTH = 1500;
const MAX_HEIGHT_PX = 120;

type MessageTextViewProps = {
  text: string;
  sharedText?: string;
  compareMode?: boolean;
};

// Function to decode HTML entities
function decodeHtmlEntities(text: string): string {
  const textarea = document.createElement("textarea");
  textarea.innerHTML = text;
  return textarea.value;
}

export function MessageTextView(props: MessageTextViewProps) {
  const { text, sharedText, compareMode } = props;
  const [isExpanded, setIsExpanded] = useState(false);
  const [shouldTruncateByHeight, setShouldTruncateByHeight] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  // Decode HTML entities in the text
  const decodedText = decodeHtmlEntities(text);
  const decodedSharedText = sharedText
    ? decodeHtmlEntities(sharedText)
    : undefined;

  useEffect(() => {
    if (contentRef.current && !isExpanded) {
      const height = contentRef.current.scrollHeight;
      setShouldTruncateByHeight(height > MAX_HEIGHT_PX);
    }
  }, [decodedText, isExpanded]);

  if (!compareMode || !sharedText) {
    const shouldTruncateByLength = decodedText.length > MAX_TEXT_LENGTH;
    const shouldTruncate = shouldTruncateByLength || shouldTruncateByHeight;
    const displayText =
      shouldTruncateByLength && !isExpanded
        ? decodedText.slice(0, MAX_TEXT_LENGTH)
        : decodedText;

    return (
      <div>
        <div
          ref={contentRef}
          className={
            shouldTruncateByHeight && !isExpanded ? "overflow-hidden" : ""
          }
          style={
            shouldTruncateByHeight && !isExpanded
              ? { maxHeight: `${MAX_HEIGHT_PX}px` }
              : {}
          }
        >
          {(() => {
            // Bold input variables in the form {{variable}}
            const parts = displayText.split(/(\{\{[^}]+\}\})/g);
            return parts.map((part, i) =>
              /^\{\{[^}]+\}\}$/.test(part) ? (
                <b key={i}>{part}</b>
              ) : (
                <React.Fragment key={i}>{part}</React.Fragment>
              )
            );
          })()}
          {shouldTruncateByLength && !isExpanded && <span>...</span>}
        </div>
        {shouldTruncate && (
          <div className="flex justify-start mt-1">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsExpanded(!isExpanded);
              }}
              className="text-xs text-blue-600 hover:text-blue-800 font-bold cursor-pointer"
            >
              {isExpanded ? "See Less" : "See More"}
            </button>
          </div>
        )}
      </div>
    );
  }

  // Find parts of text that are NOT in the shared content
  const words = decodedText.split(/(\s+)/);
  const sharedWords = decodedSharedText!.trim().split(/\s+/);

  return (
    <>
      {words.map((word, i) => {
        const cleanWord = word.trim().toLowerCase();
        const isShared = sharedWords.some(
          (sharedWord) => cleanWord && sharedWord.toLowerCase() === cleanWord
        );

        // Handle input variables
        if (/^\{\{[^}]+\}\}$/.test(word)) {
          return <b key={i}>{word}</b>;
        }

        // Highlight if it's not shared and not just whitespace
        if (!isShared && cleanWord.length > 0) {
          return (
            <mark key={i} className="bg-blue-100 text-blue-900 px-0.5 rounded">
              {word}
            </mark>
          );
        }

        return <React.Fragment key={i}>{word}</React.Fragment>;
      })}
    </>
  );
}
