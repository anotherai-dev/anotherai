import MarkdownRenderer from "@/components/MarkdownRenderer";
import { Experiment } from "@/types/models";

type Props = {
  experiment: Experiment;
};

export function OriginalResultsSection(props: Props) {
  const { experiment } = props;
  const result = experiment.result;

  if (!result) {
    return null;
  }

  return (
    <div className="mb-8">
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-3">
          Description
        </h2>
        <MarkdownRenderer content={result} className="text-gray-600 text-sm" />
      </div>
    </div>
  );
}
