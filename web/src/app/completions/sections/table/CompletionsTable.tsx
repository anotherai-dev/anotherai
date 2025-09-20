"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { PageError } from "@/components/PageError";
import { SimplePagination } from "@/components/SimplePagination";
import { SimpleTableComponent } from "@/components/SimpleTableComponent";
import { transformCompletionsData } from "@/components/utils/utils";
import { detectPaginationVariables } from "@/utils/pagination";
import { defaultQuery } from "@/utils/queries";
import { CompletionTableCell } from "./cells/CompletionTableCell";

interface CompletionsTableProps {
  data: Record<string, unknown>[];
  isLoading: boolean;
  error?: Error;
  maxHeight?: string;
  currentQuery?: string;
  heightForEmptyState?: string;
  onPageChange?: (page: number) => void;
  currentPage?: number;
}

export function CompletionsTable({
  data,
  isLoading,
  error,
  maxHeight,
  currentQuery,
  heightForEmptyState,
  onPageChange,
  currentPage: propCurrentPage,
}: CompletionsTableProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Use prop currentPage if provided, otherwise use internal state
  const [internalCurrentPage, setInternalCurrentPage] = useState(1);
  const currentPage = propCurrentPage ?? internalCurrentPage;
  const [pageSize] = useState(20); // Default page size

  // Check if the current query has pagination variables
  const hasPagination = useMemo(() => {
    return currentQuery ? detectPaginationVariables(currentQuery) : false;
  }, [currentQuery]);

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

  const handlePageChange = (page: number) => {
    if (onPageChange) {
      onPageChange(page);
    } else {
      setInternalCurrentPage(page);
    }
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
          height={heightForEmptyState}
        />
      );
    }

    return (
      <EmptyState title="No completions found." subtitle="Try adjusting your query." height={heightForEmptyState} />
    );
  }

  if (data.length === 0) {
    return null;
  }

  // If pagination is enabled, wrap the table with pagination component
  if (hasPagination) {
    // We can't know the total number of pages when using pagination variables,
    // so we'll use simple pagination that just shows current page and navigation
    const hasNextPage = data.length === pageSize; // If we got a full page, there might be more

    return (
      <div className="h-full flex flex-col bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="flex-1 min-h-0">
          <SimpleTableComponent
            columnHeaders={columnHeaders}
            data={modifiedData.map((row) =>
              columnHeaders.map((header) => <CompletionTableCell key={header} columnKey={header} value={row[header]} />)
            )}
            minCellWidth={120}
            onRowClick={hasIdColumn ? handleRowClick : undefined}
            maxHeight={undefined} // Use full available height instead of fixed height
            maxRowHeight="200px"
            enableLazyLoading={false} // Disable lazy loading when pagination is enabled
            lazyLoadBatchSize={20}
            className="border-0 rounded-none h-full" // Use full height and remove border
          />
        </div>
        <SimplePagination
          currentPage={currentPage}
          onPageChange={handlePageChange}
          isLoading={isLoading}
          hasNextPage={hasNextPage}
        />
      </div>
    );
  }

  // For non-paginated tables, use maxHeight if provided, otherwise use dynamic height
  if (maxHeight) {
    // When maxHeight is explicitly set, use original behavior
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
        enableLazyLoading={true}
        lazyLoadBatchSize={20}
      />
    );
  }

  // When no maxHeight is set, use dynamic height with consistent container
  return (
    <div className="h-full flex flex-col bg-white border border-gray-200 rounded-lg overflow-hidden">
      <SimpleTableComponent
        columnHeaders={columnHeaders}
        data={modifiedData.map((row) =>
          columnHeaders.map((header) => <CompletionTableCell key={header} columnKey={header} value={row[header]} />)
        )}
        minCellWidth={120}
        onRowClick={hasIdColumn ? handleRowClick : undefined}
        maxHeight={undefined} // Use dynamic height for consistency
        maxRowHeight="200px"
        enableLazyLoading={true}
        lazyLoadBatchSize={20}
        className="border-0 rounded-none h-full" // Use full height and remove border
      />
    </div>
  );
}
