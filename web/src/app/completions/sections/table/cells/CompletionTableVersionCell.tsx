import { ModelIconWithName } from "@/components/ModelIcon";
import { CompletionBaseTableCell } from "./CompletionBaseTableCell";

interface CompletionTableVersionCellProps {
  value: unknown;
}

export function CompletionTableVersionCell({ value }: CompletionTableVersionCellProps) {
  if (value === null || value === undefined) {
    return <span className="text-xs text-gray-400">N/A</span>;
  }

  if (typeof value === "object" && value !== null) {
    const obj = value as Record<string, unknown>;

    // Show model name as a badge
    if (obj?.model) {
      const nonDefaultEntries: Array<{ key: string; value: string }> = [];

      // Check temperature (default: 1)
      if (obj.temperature !== undefined && obj.temperature !== 1) {
        nonDefaultEntries.push({
          key: "temperature",
          value: Number(obj.temperature).toFixed(1),
        });
      }

      // Check top_p (default: 1)
      if (obj.top_p !== undefined && obj.top_p !== 1) {
        nonDefaultEntries.push({
          key: "top_p",
          value: Number(obj.top_p).toFixed(1),
        });
      }

      // Check use_cache (default: "auto")
      if (obj.use_cache !== undefined && obj.use_cache !== "auto") {
        nonDefaultEntries.push({
          key: "use_cache",
          value: String(obj.use_cache),
        });
      }

      // Check max_tokens (default: unlimited/undefined)
      if (obj.max_tokens !== undefined) {
        nonDefaultEntries.push({
          key: "max_tokens",
          value: String(obj.max_tokens),
        });
      }

      // Check stream (default: false)
      if (obj.stream !== undefined && obj.stream !== false) {
        nonDefaultEntries.push({ key: "stream", value: String(obj.stream) });
      }

      // Check include_usage (default: false)
      if (obj.include_usage !== undefined && obj.include_usage !== false) {
        nonDefaultEntries.push({
          key: "include_usage",
          value: String(obj.include_usage),
        });
      }

      // Check presence_penalty (default: 0)
      if (obj.presence_penalty !== undefined && obj.presence_penalty !== 0) {
        nonDefaultEntries.push({
          key: "presence_penalty",
          value: String(obj.presence_penalty),
        });
      }

      // Check frequency_penalty (default: 0)
      if (obj.frequency_penalty !== undefined && obj.frequency_penalty !== 0) {
        nonDefaultEntries.push({
          key: "frequency_penalty",
          value: String(obj.frequency_penalty),
        });
      }

      // Check stop (default: none/undefined)
      if (obj.stop !== undefined) {
        const stopValue = Array.isArray(obj.stop) ? obj.stop.join(", ") : String(obj.stop);
        nonDefaultEntries.push({ key: "stop", value: stopValue });
      }

      // Check tool_choice (default: "auto")
      if (obj.tool_choice !== undefined && obj.tool_choice !== "auto") {
        const toolChoice = typeof obj.tool_choice === "string" ? obj.tool_choice : JSON.stringify(obj.tool_choice);
        nonDefaultEntries.push({ key: "tool_choice", value: toolChoice });
      }

      return (
        <div className="space-y-1">
          <div className="px-2 py-1 text-xs rounded-[2px] font-medium bg-gray-200 border border-gray-300 text-gray-900 w-fit">
            <ModelIconWithName
              modelId={String(obj.model)}
              size={12}
              nameClassName="text-xs text-gray-900 font-medium"
              reasoningEffort={obj.reasoning_effort as "disabled" | "low" | "medium" | "high" | undefined}
              reasoningBudget={obj.reasoning_budget as number | undefined}
            />
          </div>
          {nonDefaultEntries.map(({ key, value }, index) => (
            <div
              key={index}
              className="flex items-center justify-between gap-2 px-2 py-1 text-xs rounded-[2px] font-medium bg-gray-100 border border-gray-200 text-gray-700 w-full"
            >
              <span className="text-gray-700 capitalize">{key}</span>
              <span className="font-semibold">{value}</span>
            </div>
          ))}
        </div>
      );
    }
  }

  return <CompletionBaseTableCell value={value} />;
}
