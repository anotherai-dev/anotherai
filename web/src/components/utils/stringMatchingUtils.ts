// String matching utilities using diff-match-patch for high-performance common substring detection
import { diff_match_patch } from "diff-match-patch";

// LRU cache for memoization - prevents recalculating same inputs
const cache = new Map<string, string>();
const MAX_CACHE_SIZE = 50;

// Reuse DMP instance for better performance
const dmp = new diff_match_patch();
// Configure for performance: disable deadline for faster processing of shorter texts
dmp.Diff_Timeout = 0;

export function findCommonSubstrings(texts: (string | null | undefined)[] | null | undefined): string {
  // Input validation
  if (!texts || texts.length === 0) return "";

  // Filter out null, undefined, and very short texts
  const validTexts = texts.filter((text): text is string => {
    if (!text || typeof text !== "string") return false;
    return text.trim().length >= 3;
  });

  if (validTexts.length === 0) return "";
  if (validTexts.length === 1) return validTexts[0];

  // Performance optimization: check cache first
  const cacheKey = validTexts.join("||");
  if (cache.has(cacheKey)) {
    return cache.get(cacheKey)!;
  }

  // Fast path: if all texts are identical, return the first one
  const firstText = validTexts[0];
  if (validTexts.every((text) => text === firstText)) {
    cache.set(cacheKey, firstText);
    return firstText;
  }

  // Performance optimization: sort by length (shortest first) to minimize comparisons
  validTexts.sort((a, b) => a.length - b.length);

  // Start with the shortest text (most likely to have the most common content)
  let commonContent = validTexts[0];

  for (let i = 1; i < validTexts.length; i++) {
    const diffs = dmp.diff_main(commonContent, validTexts[i]);

    // Performance optimization: build result more efficiently
    let result = "";
    for (const [operation, text] of diffs) {
      if (operation === 0) {
        // EQUAL operation - this text exists in both
        result += text;
      }
    }

    commonContent = result;

    // If no meaningful common content remains, cache and return empty string
    if (!commonContent.trim()) {
      cache.set(cacheKey, "");
      return "";
    }
  }

  const result = commonContent.trim();

  // Cache the result (with LRU eviction)
  if (cache.size >= MAX_CACHE_SIZE) {
    const firstKey = cache.keys().next().value;
    if (firstKey !== undefined) {
      cache.delete(firstKey);
    }
  }
  cache.set(cacheKey, result);

  return result;
}
