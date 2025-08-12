import { Completion } from "@/types/models";
import { VariablesViewer } from "../VariablesViewer/VariablesViewer";

type CompletionContextViewProps = {
  completion: Completion;
};

export function CompletionContextView(props: CompletionContextViewProps) {
  const { completion } = props;

  return (
    <div className="flex flex-col w-full h-full">
      <div className="text-base font-bold py-3 px-4 border-b border-gray-200 border-dashed text-gray-600">
        Context
      </div>
      <div className="flex-1 w-full overflow-y-auto">
        {completion.input?.variables &&
        Object.keys(completion.input.variables).length > 0 ? (
          <VariablesViewer
            variables={completion.input.variables}
            hideBorderForFirstLevel={true}
            className="px-4 pt-4"
            textSize="13px"
            maxHeight="max"
          />
        ) : (
          <div
            className="px-4 pt-4 text-gray-500 italic"
            style={{ fontSize: "13px" }}
          >
            No input variables
          </div>
        )}
      </div>
    </div>
  );
}
