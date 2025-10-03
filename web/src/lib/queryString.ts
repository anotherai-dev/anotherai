"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

type ParsedParams<K extends string, V = string> = Record<K[number], V | undefined>;

export function useParsedSearchParams<K extends string>(...keys: ReadonlyArray<K>): ParsedParams<K> {
  const params = useSearchParams();
  const parsed = useMemo(
    () => keys.reduce((m, k) => ({ ...m, [k]: params.get(k) ?? undefined }), {} as ParsedParams<K>),
    [keys, params]
  );

  return parsed;
}

export function useQueryBool(key: string) {
  const params = useSearchParams();
  const { replace } = useRouter();
  const setValue = useCallback(
    (value: boolean) => {
      const p = new URLSearchParams(params.toString());
      if (value) {
        p.set(key, "");
      } else {
        p.delete(key);
      }
      replace(`${window.location.pathname}?${p.toString()}`, { scroll: false });
    },
    [key, params, replace]
  );
  return [params.has(key), setValue] as const;
}
