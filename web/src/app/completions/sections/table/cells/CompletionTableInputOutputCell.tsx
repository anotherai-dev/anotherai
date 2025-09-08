import { cx } from "class-variance-authority";
import { PageError } from "@/components/PageError";
import { VariablesViewer } from "@/components/VariablesViewer/VariablesViewer";
import { MessagesViewer } from "@/components/messages/MessagesViewer";
import { Error, Message } from "@/types/models";

interface CompletionTableInputOutputCellProps {
  value: unknown;
  maxWidth?: string;
  sharedPartsOfPrompts?: Message[];
}

export function CompletionTableInputOutputCell({
  value,
  maxWidth = "max-w-xs",
  sharedPartsOfPrompts,
}: CompletionTableInputOutputCellProps) {
  if (value === null || value === undefined) {
    return <span className="text-xs text-gray-400">N/A</span>;
  }

  if (typeof value === "object" && value !== null) {
    const obj = value as Record<string, unknown>;
    const hasVariables = obj?.variables && typeof obj.variables === "object";
    const hasMessages = obj?.messages && Array.isArray(obj.messages);
    const hasError = obj?.error;

    // Check for internal prefixed properties
    const hasInternalVariables =
      obj?.internal_anotherai_variables && typeof obj.internal_anotherai_variables === "object";
    const hasInternalMessages = obj?.internal_anotherai_messages && Array.isArray(obj.internal_anotherai_messages);
    const hasInternalError = obj?.internal_anotherai_error;

    // Output: has error property
    if (hasError || hasInternalError) {
      const errorValue = hasError ? obj.error : obj.internal_anotherai_error;
      return <PageError error={errorValue as string | Error} showDescription={true} />;
    }

    // Has both variables and messages
    if ((hasVariables && hasMessages) || (hasInternalVariables && hasInternalMessages)) {
      const variables = hasVariables ? obj.variables : obj.internal_anotherai_variables;
      const messages = hasMessages ? obj.messages : obj.internal_anotherai_messages;
      return (
        <div className={cx("max-h-full overflow-y-auto space-y-2", maxWidth)}>
          <div>
            <VariablesViewer
              variables={variables as Record<string, unknown>}
              hideBorderForFirstLevel={true}
              textSize="xs"
              maxHeight="max"
            />
          </div>
          <div>
            <MessagesViewer
              messages={messages as Message[]}
              sharedPartsOfPrompts={sharedPartsOfPrompts}
              maxVariablesHeight="max"
            />
          </div>
        </div>
      );
    }

    // Input: has variables property only
    if (hasVariables || hasInternalVariables) {
      const variables = hasVariables ? obj.variables : obj.internal_anotherai_variables;
      return (
        <div className={cx("max-h-full overflow-y-auto", maxWidth)}>
          <VariablesViewer
            variables={variables as Record<string, unknown>}
            hideBorderForFirstLevel={true}
            textSize="xs"
            maxHeight="max"
          />
        </div>
      );
    }

    // Output: has messages property only
    if (hasMessages || hasInternalMessages) {
      const messages = hasMessages ? obj.messages : obj.internal_anotherai_messages;

      return (
        <div className={cx("max-h-full overflow-y-auto", maxWidth)}>
          <MessagesViewer
            messages={messages as Message[]}
            sharedPartsOfPrompts={sharedPartsOfPrompts}
            maxVariablesHeight="max"
          />
        </div>
      );
    }

    // Fallback: show raw object structure for debugging
    return (
      <div className={cx("text-xs text-gray-600 overflow-hidden", maxWidth)}>
        <pre className="whitespace-pre-wrap">{JSON.stringify(obj, null, 2).substring(0, 200)}...</pre>
      </div>
    );
  }

  return <span className="text-xs text-gray-400">N/A</span>;
}
