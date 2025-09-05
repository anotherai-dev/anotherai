import { ModelIconWithName } from "@/components/ModelIcon";
import { SchemaViewer } from "@/components/SchemaViewer";
import { MessagesViewer } from "@/components/messages/MessagesViewer";
import { Message, OutputSchema, Tool } from "@/types/models";

export function renderValue(key: string, value: unknown) {
  switch (key) {
    case "model":
      return <ModelIconWithName modelId={String(value)} size={12} nameClassName="text-xs text-gray-900" />;
    case "temperature":
    case "top_p":
      return <span className="text-xs text-gray-900">{String(value)}</span>;
    case "use_cache":
    case "max_tokens":
      return <span className="text-xs text-gray-900">{String(value)}</span>;
    case "stream":
    case "include_usage":
      return <span className="text-xs text-gray-900">{value ? "true" : "false"}</span>;
    case "presence_penalty":
    case "frequency_penalty":
      return <span className="text-xs text-gray-900">{String(value)}</span>;
    case "stop":
      return <span className="text-xs text-gray-900">{Array.isArray(value) ? value.join(", ") : String(value)}</span>;
    case "tool_choice":
      return <span className="text-xs text-gray-900">{typeof value === "string" ? value : JSON.stringify(value)}</span>;
    case "tools":
      const tools = value as Tool[];
      return (
        <span className="text-xs text-gray-900">
          {tools.length === 0 ? "No tools available" : `${tools.length} tool(s)`}
        </span>
      );
    case "prompt":
      const prompt = value as Message[];
      return prompt && prompt.length > 0 ? (
        <div className="text-xs text-gray-900">
          <MessagesViewer messages={prompt} />
        </div>
      ) : (
        <span className="text-xs text-gray-900">No prompt</span>
      );
    case "output_schema":
      const schema = value as OutputSchema;
      return schema ? (
        <div className="text-xs text-gray-900">
          <SchemaViewer schema={schema} />
        </div>
      ) : (
        <span className="text-xs text-gray-900">No schema</span>
      );
    default:
      return <span className="text-xs text-gray-900">{String(value)}</span>;
  }
}
