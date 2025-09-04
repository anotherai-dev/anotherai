"use client";

import { Suspense } from "react";
import { PageHeader } from "@/components/PageHeader";
import { FilterCompletionsInstructions } from "@/components/completion-modal/FilterCompletionsInstructions";
import { useCompletionsListSync } from "@/hooks/useCompletionsListSync";
import { useCompletionsQuery } from "@/store/completions";
import { defaultQuery } from "@/utils/queries";
import { SearchSection } from "./sections/SearchSection";
import { CompletionsTable } from "./sections/table/CompletionsTable";
import { useQuerySync } from "./useQuerySync";

export const dynamic = "force-dynamic";

function CompletionsPageContent() {
  const [query, setQuery] = useQuerySync(defaultQuery);

  const placeholder = "Enter SQL query (e.g., SELECT * FROM completions WHERE model = 'gpt-4') to search completions";

  const { data, isLoading, error } = useCompletionsQuery(query);

  // Sync completions data with stored completions list for modal navigation
  useCompletionsListSync(data);

  return (
    <div className="flex flex-col w-full h-full mx-auto px-4 pt-4 pb-8 gap-4 bg-gray-50">
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

      <CompletionsTable data={data ?? []} isLoading={isLoading} error={error} currentQuery={query} />
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
