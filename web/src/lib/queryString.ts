"use client";

import { useSearchParams } from "next/navigation";
import { useMemo } from "react";

type ParsedParams<K extends string, V = string> = Record<K[number], V | undefined>;

export function useParsedSearchParams<K extends string>(...keys: ReadonlyArray<K>): ParsedParams<K> {
  const params = useSearchParams();
  const parsed = useMemo(
    () => keys.reduce((m, k) => ({ ...m, [k]: params.get(k) ?? undefined }), {} as ParsedParams<K>),
    [keys, params]
  );

  return parsed;
}
