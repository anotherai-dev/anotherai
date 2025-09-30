import { useMemo } from "react";
import { formatCurrency, isDateValue, parseJSONValue } from "@/components/utils/utils";
import { Message } from "@/types/models";
import CompletionBaseTableCell from "./CompletionBaseTableCell";
import CompletionObjectTableCell from "./CompletionObjectTableCell";
import CompletionOutputSchemaCell from "./CompletionOutputSchemaCell";
import CompletionTableBadgeCell from "./CompletionTableBadgeCell";
import CompletionTableDateCell from "./CompletionTableDateCell";
import CompletionTableMetadataCell from "./CompletionTableMetadataCell";
import CompletionTableVersionCell from "./CompletionTableVersionCell";

interface Props {
  columnKey: string;
  value: unknown;
  maxWidth?: string;
  sharedPartsOfPrompts?: Message[];
  sharedKeypathsOfSchemas?: string[];
}

export function CompletionTableCell(props: Props) {
  const { columnKey, value, maxWidth, sharedPartsOfPrompts, sharedKeypathsOfSchemas } = props;

  const parsedJSON = useMemo(() => parseJSONValue(value), [value]);

  if (parsedJSON !== null) {
    switch (columnKey) {
      case "version":
        return <CompletionTableVersionCell value={parsedJSON} />;
      case "metadata":
        return <CompletionTableMetadataCell value={parsedJSON} />;
      case "output_schema":
        return (
          <CompletionOutputSchemaCell
            value={parsedJSON}
            maxWidth={maxWidth}
            sharedKeypathsOfSchemas={sharedKeypathsOfSchemas}
          />
        );
      default:
        return (
          <CompletionObjectTableCell
            value={parsedJSON}
            maxWidth={maxWidth}
            sharedPartsOfPrompts={sharedPartsOfPrompts}
          />
        );
    }
  }

  switch (columnKey) {
    case "updated_at":
    case "created_at":
      return <CompletionTableDateCell value={value} format="relative" />;
    case "model":
    case "version_model":
      return <CompletionTableVersionCell value={{ model: value }} />;
    case "cost_millionth_usd":
      return <CompletionTableBadgeCell value={Number(value)} variant="white" rounded="2px" />;
    case "cost_usd":
      return (
        <CompletionTableBadgeCell
          value={`${formatCurrency(Number(value), 1000)} (Per 1k)`}
          variant="white"
          rounded="2px"
        />
      );
    case "duration_ds":
      return <CompletionTableBadgeCell value={`${(Number(value) / 10).toFixed(2)}s`} variant="white" rounded="2px" />;
    default:
      if (isDateValue(value)) {
        return <CompletionTableDateCell value={value} format="relative" />;
      }
      return <CompletionBaseTableCell value={value} />;
  }
}
