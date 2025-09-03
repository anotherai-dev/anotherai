"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

export function useQuerySync(defaultQuery: string) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const queryFromUrl = searchParams.get("query");
  const [query, setQuery] = useState(queryFromUrl || defaultQuery);

  // Read newQuery parameter and update query, then remove newQuery from URL
  useEffect(() => {
    const newQueryParam = searchParams.get("newQuery");
    if (newQueryParam !== null) {
      setQuery(newQueryParam);

      // Remove newQuery parameter from URL
      const params = new URLSearchParams(searchParams);
      params.delete("newQuery");
      const newUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}`;
      router.replace(newUrl, { scroll: false });
    }
  }, [searchParams, router]);

  // Update URL query parameter when query state changes
  useEffect(() => {
    const currentUrlQuery = searchParams.get("query");

    // Don't update URL if this matches what's already there
    if (currentUrlQuery === query || (currentUrlQuery === null && query === defaultQuery)) {
      return;
    }

    const params = new URLSearchParams(searchParams);
    if (query === defaultQuery) {
      params.delete("query");
    } else {
      params.set("query", query);
    }

    const newUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}`;
    router.replace(newUrl, { scroll: false });
  }, [query, router, searchParams, defaultQuery]);

  return [query, setQuery] as const;
}
