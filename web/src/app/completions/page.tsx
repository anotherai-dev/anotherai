"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { FilterCompletionsInstructions } from "@/components/completion-modal/FilterCompletionsInstructions";
import { useCompletionsListSync } from "@/hooks/useCompletionsListSync";
import { useCompletionsQuery } from "@/store/completions";
import { processPaginationQuery } from "@/utils/pagination";
import { defaultQuery } from "@/utils/queries";
import { SearchSection } from "./sections/SearchSection";
import { CompletionsTable } from "./sections/table/CompletionsTable";
import { useQuerySync } from "./useQuerySync";

export const dynamic = "force-dynamic";

function CompletionsPageContent() {
  const [query, setQuery] = useQuerySync(defaultQuery);
  const [currentPage, setCurrentPage] = useState(1);

  const placeholder = "Enter SQL query (e.g., SELECT * FROM completions WHERE model = 'gpt-4') to search completions";

  // Process the query to handle pagination variables before sending to API
  const processedQuery = useMemo(() => {
    const { processedQuery } = processPaginationQuery(query, currentPage, 20);
    return processedQuery;
  }, [query, currentPage]);

  const { data, isLoading, error } = useCompletionsQuery(processedQuery);

  // Reset to page 1 when query changes
  useEffect(() => {
    setCurrentPage(1);
  }, [query]);

  // Sync completions data with stored completions list for modal navigation
  useCompletionsListSync(data);

  return (
    <div className="flex flex-col w-full h-full mx-auto px-4 pt-4 pb-4 gap-4 bg-gray-50">
      <PageHeader
        breadcrumbs={[]}
        title="Completions"
        description="Search through completions using SQL queries, view detailed completion lists, and open individual completion details for analysis"
        descriptionRightContent={<FilterCompletionsInstructions />}
        className="pb-2"
      />

      <SearchSection
        onSearch={(newQuery) => setQuery(newQuery)}
        defaultValue={query}
        placeholder={placeholder}
        isLoading={isLoading}
      />

      <div className="flex-1 min-h-0">
        <CompletionsTable
          data={data ?? []}
          isLoading={isLoading}
          error={error}
          currentQuery={query}
          onPageChange={setCurrentPage}
          currentPage={currentPage}
        />
      </div>
    </div>
  );
}

export default function CompletionsPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <CompletionsPageContent />
    </Suspense>
  );
}
