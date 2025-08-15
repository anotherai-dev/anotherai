import { Copy } from "lucide-react";
import React, { useCallback, useState } from "react";
import { MessageContentView } from "@/components/messages/MessageContentView";
import { formatDuration, getRoleDisplay } from "@/components/utils/utils";
import { Annotation, Message } from "@/types/models";
import { useToast } from "../ToastProvider";

type MessageViewProps = {
  message: Message;
  index: number;
  sharedPartsOfPrompts?: Message[];
  annotations?: Annotation[];
  onKeypathSelect?: (keyPath: string) => void;
};

export function MessageView(props: MessageViewProps) {
  const { message, index, sharedPartsOfPrompts, annotations, onKeypathSelect } = props;
  const [isHovered, setIsHovered] = useState(false);
  const { showToast } = useToast();

  const hasCostOrDuration = message.cost_usd || message.duration_seconds;
  const hasMetrics = message.metrics && message.metrics.length > 0;

  const copyMessageContent = useCallback(async () => {
    let textToCopy = "";

    if (typeof message.content === "string") {
      textToCopy = message.content;
    } else if (Array.isArray(message.content)) {
      const contentParts = message.content.map((item) => {
        if (item.text && item.text.trim() !== "") {
          return item.text;
        } else {
          // For non-text items (images, tool calls, etc.), stringify them
          return JSON.stringify(item, null, 2);
        }
      });

      textToCopy = contentParts.join("\n\n");
    } else {
      // For any other content type, stringify it
      textToCopy = JSON.stringify(message.content, null, 2);
    }

    if (textToCopy.trim() === "") {
      showToast("No content to copy");
      return;
    }

    try {
      await navigator.clipboard.writeText(textToCopy);
      showToast("Copied message content");
    } catch (err) {
      console.error("Failed to copy to clipboard:", err);
      showToast("Failed to copy");
    }
  }, [message.content, showToast]);

  return (
    <div
      className="border border-gray-200 rounded-[2px] bg-white relative"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className={`flex items-center gap-2 px-3 py-2 bg-transparent rounded-t-[2px]`}>
        <span className="text-[12.5px] font-semibold text-gray-700">{getRoleDisplay(message.role)}</span>
      </div>
      <div className="pt-1 pb-3 px-3 bg-transparent">
        <MessageContentView
          content={message.content}
          contentToCompareTo={
            sharedPartsOfPrompts?.[index]?.role === message.role ? sharedPartsOfPrompts[index]?.content : undefined
          }
          compareMode={sharedPartsOfPrompts !== undefined}
          annotations={annotations}
          onKeypathSelect={onKeypathSelect}
        />
      </div>
      {(hasCostOrDuration || hasMetrics) && (
        <div className="border-t border-gray-200">
          {hasCostOrDuration && (
            <div className="grid grid-cols-2 gap-0">
              <div className="px-3 py-3 text-xs bg-gray-50 flex justify-between items-center">
                <span className="font-medium text-gray-600">Cost</span>
                <span className="text-gray-800">${(message.cost_usd || 0).toFixed(5)}</span>
              </div>
              <div className="px-3 py-3 text-xs bg-gray-50 border-l border-gray-200 flex justify-between items-center">
                <span className="font-medium text-gray-600">Duration</span>
                <span className="text-gray-800">{formatDuration(message.duration_seconds || 0)}</span>
              </div>
            </div>
          )}
          {hasMetrics && (
            <div className={`${hasCostOrDuration ? "border-t border-gray-200" : ""}`}>
              {message.metrics?.map(({ key, average }) => (
                <div
                  key={key}
                  className="px-3 py-3 text-xs bg-gray-50 flex justify-between items-center border-b border-gray-200 last:border-b-0"
                >
                  <span className="font-medium text-gray-600 capitalize">{key.replace(/_/g, " ")}</span>
                  <span className="text-gray-800">{average.toFixed(2)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {isHovered && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            copyMessageContent();
          }}
          className="absolute top-1 right-1 p-1 bg-white border border-gray-200 rounded-[2px] hover:bg-gray-100 transition-colors cursor-pointer"
          title="Copy message content"
        >
          <Copy size={12} />
        </button>
      )}
    </div>
  );
}
