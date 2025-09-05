import { VariablesViewer } from "@/components/VariablesViewer/VariablesViewer";
import { MessageTextView } from "@/components/messages/MessageTextView";
import { ToolCallRequestView, ToolCallResultView } from "@/components/messages/ToolCallView";
import { UniversalFileViewer } from "@/components/messages/UniversalFileViewer";
import { Annotation, MessageContent } from "@/types/models";

type MessageContentViewProps = {
  content: string | Record<string, unknown> | MessageContent[];
  contentToCompareTo?: string | Record<string, unknown> | MessageContent[];
  compareMode?: boolean;
  annotations?: Annotation[];
  onKeypathSelect?: (keyPath: string) => void;
  maxVariablesHeight?: string;
};

export function MessageContentView(props: MessageContentViewProps) {
  const { content, contentToCompareTo, compareMode, annotations, onKeypathSelect, maxVariablesHeight } = props;

  // Handle direct object content (structured output)
  if (content && typeof content === "object" && !Array.isArray(content)) {
    return (
      <div className="text-[12.5px]">
        <VariablesViewer
          variables={content as Record<string, unknown>}
          hideBorderForFirstLevel={true}
          annotations={annotations}
          onKeypathSelect={onKeypathSelect}
          maxHeight={maxVariablesHeight}
        />
      </div>
    );
  }

  if (typeof content === "string") {
    const sharedContent = typeof contentToCompareTo === "string" ? contentToCompareTo : undefined;

    // Check if string content is parsable as JSON object
    try {
      const parsed = JSON.parse(content);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return (
          <div className="text-[12.5px]">
            <VariablesViewer
              variables={parsed as Record<string, unknown>}
              hideBorderForFirstLevel={true}
              annotations={annotations}
              onKeypathSelect={onKeypathSelect}
              maxHeight={maxVariablesHeight}
            />
          </div>
        );
      }
    } catch {
      // If JSON parsing fails, fall through to normal text rendering
    }

    return (
      <div className="text-[12.5px] text-gray-900 whitespace-pre-wrap">
        <MessageTextView text={content} sharedText={sharedContent} compareMode={compareMode} />
      </div>
    );
  }

  // Handle array of content objects
  return (
    <div className="space-y-1">
      {content.map((item, index) => {
        // Get corresponding shared content if available
        const sharedContentArray = Array.isArray(contentToCompareTo) ? contentToCompareTo : undefined;
        const sharedItem = sharedContentArray?.[index];
        const sharedText = sharedItem?.text;

        return (
          <div key={index} className="text-[12.5px] text-gray-900">
            {item.text && (
              <div className="whitespace-pre-wrap break-words">
                <MessageTextView text={item.text} sharedText={sharedText} compareMode={compareMode} />
              </div>
            )}
            {item.object && (
              <div>
                {Array.isArray(item.object) ? (
                  <VariablesViewer
                    variables={{ items: item.object }}
                    hideBorderForFirstLevel={true}
                    annotations={annotations}
                    onKeypathSelect={onKeypathSelect}
                    maxHeight={maxVariablesHeight}
                  />
                ) : (
                  <VariablesViewer
                    variables={item.object as Record<string, unknown>}
                    hideBorderForFirstLevel={true}
                    annotations={annotations}
                    onKeypathSelect={onKeypathSelect}
                    maxHeight={maxVariablesHeight}
                  />
                )}
              </div>
            )}
            {item.image_url && (
              <div className="mt-2">
                <UniversalFileViewer url={item.image_url} />
              </div>
            )}
            {item.file && (item.file.url || item.file.storage_url) && (
              <UniversalFileViewer url={item.file.storage_url || item.file.url || ""} />
            )}
            {item.audio_url && <UniversalFileViewer url={item.audio_url} />}
            {item.tool_call_request && <ToolCallRequestView toolCallRequest={item.tool_call_request} />}
            {item.tool_call_result && <ToolCallResultView toolCallResult={item.tool_call_result} />}
          </div>
        );
      })}
    </div>
  );
}
