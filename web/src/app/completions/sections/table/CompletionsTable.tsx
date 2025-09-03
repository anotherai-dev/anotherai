"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo } from "react";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { PageError } from "@/components/PageError";
import { SimpleTableComponent } from "@/components/SimpleTableComponent";
import { transformCompletionsData } from "@/components/utils/utils";
import { defaultQuery } from "@/utils/queries";
import { CompletionTableCell } from "./cells/CompletionTableCell";

interface CompletionsTableProps {
  data: Record<string, unknown>[];
  isLoading: boolean;
  error?: Error;
  maxHeight?: string;
  currentQuery?: string;
}

export function CompletionsTable({ data, isLoading, error, maxHeight, currentQuery }: CompletionsTableProps) {
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

  if (isLoading) {
    return <LoadingState />;
  }

  if (!isLoading && data.length === 0) {
    const isDefaultQuery = currentQuery === defaultQuery;

    if (isDefaultQuery) {
      return (
        <EmptyState
          title="No completions created yet."
          subtitle="Start by creating your first completion using the AnotherAI API and MCP."
          documentationUrl="https://docs.anotherai.dev"
        />
      );
    }

    return <EmptyState title="No completions found." subtitle="Try adjusting your query." />;
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
