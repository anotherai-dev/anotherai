import { PageError } from "@/components/PageError";
import { VariablesViewer } from "@/components/VariablesViewer/VariablesViewer";
import { ToolCallRequest, ToolCallResult } from "@/types/models";

interface ToolCallRequestViewProps {
  toolCallRequest: ToolCallRequest;
}

interface ToolCallResultViewProps {
  toolCallResult: ToolCallResult;
}

export function ToolCallRequestView({
  toolCallRequest,
}: ToolCallRequestViewProps) {
  // Handle both field name variations
  const toolName =
    toolCallRequest.name ||
    ((toolCallRequest as unknown as Record<string, unknown>)
      .tool_name as string);
  const toolArguments =
    toolCallRequest.arguments ||
    ((toolCallRequest as unknown as Record<string, unknown>)
      .tool_input_dict as Record<string, unknown>);

  return (
    <div className="border border-gray-200 rounded-[2px] bg-slate-50 p-3 my-2">
      <div className="mb-2">
        <span className="text-xs font-semibold text-gray-800">
          Tool Call Request
        </span>
      </div>

      {toolName && (
        <div className="mb-2">
          <span className="text-xs bg-gray-200 text-gray-900 font-medium px-2 py-1 rounded-[2px] border border-gray-300">
            {toolName}
          </span>
        </div>
      )}

      {toolArguments && Object.keys(toolArguments).length > 0 && (
        <div className="mt-2 border border-gray-200 rounded-[2px] bg-white p-2">
          <VariablesViewer
            variables={toolArguments}
            hideBorderForFirstLevel={true}
            textSize="xs"
          />
        </div>
      )}

      <div className="text-xs text-gray-600 mt-2">id: {toolCallRequest.id}</div>
    </div>
  );
}

export function ToolCallResultView({
  toolCallResult,
}: ToolCallResultViewProps) {
  // Parse the output if it's a JSON string
  let parsedOutput: Record<string, unknown> | unknown = toolCallResult.output;
  if (typeof toolCallResult.output === "string") {
    try {
      parsedOutput = JSON.parse(toolCallResult.output);
    } catch {
      // If parsing fails, keep it as a string
      parsedOutput = { result: toolCallResult.output };
    }
  }

  return (
    <div className="border border-gray-200 rounded-[2px] bg-slate-50 p-3 my-2">
      <div className="mb-2">
        <span className="text-xs font-semibold text-gray-800">
          Tool Call Response
        </span>
      </div>

      {toolCallResult.error ? (
        <div className="mt-2">
          <PageError error={toolCallResult.error} showDescription={true} />
        </div>
      ) : parsedOutput ? (
        <div className="mt-2 border border-gray-200 rounded-[2px] bg-white p-2">
          <VariablesViewer
            variables={parsedOutput as Record<string, unknown>}
            hideBorderForFirstLevel={true}
            textSize="xs"
          />
        </div>
      ) : (
        <div className="mt-2 text-xs text-gray-500 italic">
          No output data available
        </div>
      )}

      <div className="text-xs text-gray-600 mt-2">id: {toolCallResult.id}</div>
    </div>
  );
}
