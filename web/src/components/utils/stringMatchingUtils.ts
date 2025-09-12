// String matching utilities using diff-match-patch for high-performance common substring detection
import { diff_match_patch } from "diff-match-patch";

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

  const dmp = new diff_match_patch();
  const commonFragments = new Set<string>();

  // Compare each pair of texts to find common substrings
  for (let i = 0; i < validTexts.length; i++) {
    for (let j = i + 1; j < validTexts.length; j++) {
      const diffs = dmp.diff_main(validTexts[i], validTexts[j]);

      // Extract common parts (EQUAL operations in diff)
      diffs.forEach(([operation, text]) => {
        if (operation === 0 && text.trim().length >= 3) {
          // EQUAL operation
          commonFragments.add(text.trim());
        }
      });
    }
  }

  // Convert to array, sort by length (longest first), and join
  const fragments = Array.from(commonFragments)
    .sort((a, b) => b.length - a.length)
    .slice(0, 10);

  return fragments.join(" ").trim();
}
