import { CompletionTableCell } from "@/app/completions/sections/table/cells/CompletionTableCell";
import { SimpleTableComponent } from "@/components/SimpleTableComponent";
import { getVersionKeyDisplayName } from "@/components/utils/utils";
import { ExtendedVersion, Message } from "@/types/models";

interface CompareSectionProps {
  keys: string[];
  currentWithDefaults?: ExtendedVersion;
  newWithDefaults?: ExtendedVersion;
  isDiffMode?: boolean;
  sharedPartsOfPrompts?: Message[];
  sharedKeypathsOfSchemas?: string[];
}

export function CompareSection({
  keys,
  currentWithDefaults,
  newWithDefaults,
  isDiffMode = false,
  sharedPartsOfPrompts,
  sharedKeypathsOfSchemas,
}: CompareSectionProps) {
  if (keys.length === 0) return null;

  // Prepare table headers
  const columnHeaders = ["", "Currently Deployed", "Proposed Deployment"];

  // Prepare table data
  const data = keys.map((key) => {
    const currentValue = currentWithDefaults?.[key as keyof typeof currentWithDefaults];
    const newValue = newWithDefaults?.[key as keyof typeof newWithDefaults];

    return [
      <span key="property" className="text-[12px] font-medium text-gray-900">
        {getVersionKeyDisplayName(key)}
      </span>,
      <CompletionTableCell key="current" columnKey={key} value={currentValue} maxWidth="w-full" />,
      <CompletionTableCell
        key="new"
        columnKey={key}
        value={newValue}
        maxWidth="w-full"
        sharedPartsOfPrompts={isDiffMode ? sharedPartsOfPrompts : undefined}
        sharedKeypathsOfSchemas={isDiffMode ? sharedKeypathsOfSchemas : undefined}
      />,
    ];
  });

  return (
    <SimpleTableComponent
      columnHeaders={columnHeaders}
      data={data}
      minCellWidth={120}
      columnWidths={["20%", "40%", "40%"]}
    />
  );
}
