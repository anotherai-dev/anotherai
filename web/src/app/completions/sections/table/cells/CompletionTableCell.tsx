import { isDateValue, parseJSONValue } from "@/components/utils/utils";
import { CompletionBaseTableCell } from "./CompletionBaseTableCell";
import { CompletionObjectTableCell } from "./CompletionObjectTableCell";
import { CompletionTableBadgeCell } from "./CompletionTableBadgeCell";
import { CompletionTableDateCell } from "./CompletionTableDateCell";
import { CompletionTableMetadataCell } from "./CompletionTableMetadataCell";
import { CompletionTableVersionCell } from "./CompletionTableVersionCell";

interface Props {
  columnKey: string;
  value: unknown;
}

export function CompletionTableCell(props: Props) {
  const { columnKey, value } = props;

  const parsedJSON = parseJSONValue(value);

  if (parsedJSON !== null) {
    switch (columnKey) {
      case "version":
        return <CompletionTableVersionCell value={parsedJSON} />;
      case "metadata":
        return <CompletionTableMetadataCell value={parsedJSON} />;
      default:
        return <CompletionObjectTableCell value={parsedJSON} />;
    }
  }

  switch (columnKey) {
    case "updated_at":
    case "created_at":
      return <CompletionTableDateCell value={value} format="relative" />;
    case "model":
    case "version_model":
      return <CompletionTableBadgeCell value={value} variant="default" rounded="2px" />;
    case "cost_millionth_usd":
      return <CompletionTableBadgeCell value={Number(value)} variant="white" rounded="2px" />;
    case "cost_usd":
      return <CompletionTableBadgeCell value={`$${Number(value).toFixed(6)}`} variant="white" rounded="2px" />;
    case "duration_ds":
      return <CompletionTableBadgeCell value={`${(Number(value) / 10).toFixed(2)}s`} variant="white" rounded="2px" />;
    default:
      if (isDateValue(value)) {
        return <CompletionTableDateCell value={value} format="relative" />;
      }
      return <CompletionBaseTableCell value={value} />;
  }
}
