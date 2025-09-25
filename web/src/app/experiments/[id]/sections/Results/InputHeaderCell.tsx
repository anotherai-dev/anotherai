import { memo } from "react";
import { VariablesViewer } from "@/components/VariablesViewer/VariablesViewer";
import { MessagesViewer } from "@/components/messages/MessagesViewer";
import { Input } from "@/types/models";

type InputHeaderCellProps = {
  input: Input;
  index: number;
};

function InputHeaderCell(props: InputHeaderCellProps) {
  const { input, index } = props;

  return (
    <div className="flex flex-col h-full max-h-[800px] overflow-hidden">
      <div className="font-semibold text-sm mb-2">Input {index + 1}</div>
      <div className="flex-1 space-y-2 overflow-y-auto">
        {input.variables && Object.keys(input.variables).length > 0 && <VariablesViewer variables={input.variables} />}
        {input.messages && input.messages.length > 0 && <MessagesViewer messages={input.messages} />}
      </div>
    </div>
  );
}

// Helper function to shallow compare Input objects
function areInputsEqual(prev: Input, next: Input): boolean {
  return prev.id === next.id && prev.variables === next.variables && prev.messages === next.messages;
}

export default memo(InputHeaderCell, (prevProps, nextProps) => {
  return prevProps.index === nextProps.index && areInputsEqual(prevProps.input, nextProps.input);
});
