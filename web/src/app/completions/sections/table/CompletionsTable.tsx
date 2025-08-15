"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo } from "react";
import { PageError } from "@/components/PageError";
import { SimpleTableComponent } from "@/components/SimpleTableComponent";
import { transformCompletionsData } from "@/components/utils/utils";
import { CompletionTableCell } from "./cells/CompletionTableCell";

interface CompletionsTableProps {
  data: Record<string, unknown>[];
  isLoading: boolean;
  error?: Error;
  maxHeight?: string;
}

export function CompletionsTable({ data, isLoading, error, maxHeight }: CompletionsTableProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Transform data to split input field into input_messages and input_variables
  const modifiedData = useMemo(() => transformCompletionsData(data), [data]);

  // Extract column headers from the first row of modified data, excluding 'id' unless it's the only column
  const columnHeaders = useMemo(() => {
    const allKeys = modifiedData.length > 0 ? Object.keys(modifiedData[0]) : [];
    return allKeys.length > 1 ? allKeys.filter((key) => key !== "id") : allKeys;
  }, [modifiedData]);

  // Check if the data contains an 'id' column to determine if rows should be clickable
  const hasIdColumn = useMemo(() => {
    if (data.length === 0) {
      return false;
    }

    // Check if the first row has an 'id' field
    return "id" in data[0];
  }, [data]);

  const handleRowClick = (rowIndex: number) => {
    const row = data[rowIndex];
    const completionId = row.id as string;

    if (!completionId) {
      console.warn("No completion ID found for row:", row);
      return;
    }

    const params = new URLSearchParams(searchParams);
    params.set("showCompletionModal", completionId);
    const newUrl = `${window.location.pathname}?${params.toString()}`;
    router.push(newUrl, { scroll: false });
  };

  if (error) {
    return <PageError error={error.message} />;
  }

  if (!isLoading && data.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
        <p className="text-gray-500">No completions found. Try adjusting your query.</p>
      </div>
    );
  }

  if (data.length === 0) {
    return null;
  }

  return (
    <SimpleTableComponent
      columnHeaders={columnHeaders}
      data={modifiedData.map((row) =>
        columnHeaders.map((header) => <CompletionTableCell key={header} columnKey={header} value={row[header]} />)
      )}
      minCellWidth={120}
      onRowClick={hasIdColumn ? handleRowClick : undefined}
      maxHeight={maxHeight}
      maxRowHeight="200px"
    />
  );
}
