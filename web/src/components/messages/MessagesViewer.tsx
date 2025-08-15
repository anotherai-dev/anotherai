import { cx } from "class-variance-authority";
import React from "react";
import { MessageView } from "@/components/messages/MessageView";
import { Annotation, Message } from "@/types/models";

type MessagesViewerProps = {
  messages: Message[];
  className?: string;
  sharedPartsOfPrompts?: Message[];
  annotations?: Annotation[];
  onKeypathSelect?: (keyPath: string) => void;
};

export function MessagesViewer(props: MessagesViewerProps) {
  const { messages, className = "", sharedPartsOfPrompts, annotations, onKeypathSelect } = props;

  // Filter out messages with empty content
  const filteredMessages = messages.filter((message) => {
    if (typeof message.content === "string") {
      return message.content.trim() !== "";
    }
    if (message.content && typeof message.content === "object" && !Array.isArray(message.content)) {
      // Direct object content (structured output)
      return Object.keys(message.content).length > 0;
    }
    if (Array.isArray(message.content)) {
      return (
        message.content.length > 0 &&
        message.content.some(
          (item) =>
            (item.text && item.text.trim() !== "") ||
            item.object ||
            item.image_url ||
            item.audio_url ||
            item.tool_call_request ||
            item.tool_call_result
        )
      );
    }
    return false;
  });

  return (
    <div className={cx("space-y-2", className)}>
      {filteredMessages.map((message, index) => (
        <MessageView
          key={index}
          message={message}
          index={index}
          sharedPartsOfPrompts={sharedPartsOfPrompts}
          annotations={annotations}
          onKeypathSelect={onKeypathSelect}
        />
      ))}
    </div>
  );
}
