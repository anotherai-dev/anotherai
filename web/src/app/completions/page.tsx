"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { HeaderSection } from "@/components/HeaderSection";
import { useCompletionsListSync } from "@/hooks/useCompletionsListSync";
import { useCompletionsQuery } from "@/store/completions";
import { defaultQuery } from "@/utils/queries";
import { SearchSection } from "./sections/SearchSection";
import { CompletionsTable } from "./sections/table/CompletionsTable";

export const dynamic = "force-dynamic";

function CompletionsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const queryFromUrl = searchParams.get("query");
  const [value, setValue] = useState(queryFromUrl || defaultQuery);

  const placeholder = "Enter SQL query (e.g., SELECT * FROM completions WHERE model = 'gpt-4') to search completions";

  const { data, isLoading, error } = useCompletionsQuery(value);

  // Sync completions data with stored completions list for modal navigation
  useCompletionsListSync(data);

  // Sync URL parameters with state, avoiding circular updates
  useEffect(() => {
    const urlQuery = searchParams.get("query");
    if (urlQuery !== null) {
      setValue(urlQuery);
    }
  }, [searchParams]);

  // Update URL when query changes (but not if it matches what's already in URL)
  useEffect(() => {
    const currentUrlQuery = searchParams.get("query");

    // Don't update URL if this matches what's already there
    if (currentUrlQuery === value || (currentUrlQuery === null && value === defaultQuery)) {
      return;
    }

    const params = new URLSearchParams(searchParams);
    if (value === defaultQuery) {
      params.delete("query");
    } else {
      params.set("query", value);
    }

    const newUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}`;
    router.replace(newUrl, { scroll: false });
  }, [value, router, searchParams]);

  return (
    <div className="flex flex-col w-full h-full mx-auto px-4 py-8 gap-6 bg-gray-50">
      <HeaderSection
        title="Completions"
        description="Search through completions using SQL queries, view detailed completion lists, and open individual completion details for analysis"
      />

      <SearchSection
        onSearch={(query) => setValue(query)}
        defaultValue={value}
        placeholder={placeholder}
        isLoading={isLoading}
      />

      <CompletionsTable data={data ?? []} isLoading={isLoading} error={error} />
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
