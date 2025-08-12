// String matching utilities for finding common substrings and patterns
// Optimized for both small and large datasets with consistent behavior

// Constants for consistent behavior across approaches
const MIN_WORD_LENGTH = 3;
const MIN_PHRASE_LENGTH = 12; // characters
const MAX_PHRASE_LENGTH = 120; // characters
const WHITESPACE_RATIO_THRESHOLD = 0.5;
const MAX_SENTENCES_TO_PROCESS = 15;
const MAX_PHRASE_WORDS = 6;
const MIN_PHRASE_WORDS = 3;

// Helper function for efficient Set intersection
function intersectSets<T>(sets: Set<T>[]): Set<T> {
  if (sets.length === 0) return new Set();
  if (sets.length === 1) return new Set(sets[0]);

  let result = new Set(sets[0]);
  for (let i = 1; i < sets.length; i++) {
    const intersection = new Set<T>();
    for (const item of result) {
      if (sets[i].has(item)) {
        intersection.add(item);
      }
    }
    result = intersection;
    if (result.size === 0) break; // Early termination
  }
  return result;
}

// Helper function to remove contained substrings efficiently
function removeContainedSubstrings(strings: string[]): string[] {
  if (strings.length <= 1) return strings;

  // Sort by length (longest first) for more efficient filtering
  const sorted = [...strings].sort((a, b) => b.length - a.length);
  const result: string[] = [];

  for (const str of sorted) {
    // Check if this string is contained in any already accepted string
    const isContained = result.some(
      (existing) => existing.length > str.length && existing.includes(str)
    );
    if (!isContained) {
      result.push(str);
    }
  }

  return result.sort((a, b) => b.length - a.length); // Maintain length order
}

// Helper function to find longest common substrings between multiple texts
// Optimized for large datasets with consistent behavior across approaches
export function findCommonSubstrings(texts: string[]): string {
  // Input validation
  if (!texts || texts.length === 0) return "";
  // Filter out null, undefined, and very short texts
  const validTexts = texts.filter((text) => {
    if (!text || typeof text !== "string") return false;
    return text.trim().length >= 3;
  });
  if (validTexts.length === 0) return "";
  if (validTexts.length === 1) return validTexts[0];

  // Performance optimization: if we have many texts or very long texts, use a more efficient approach
  const totalLength = validTexts.reduce((sum, text) => sum + text.length, 0);
  const shouldUseOptimizedApproach =
    validTexts.length > 10 || totalLength > 10000;

  if (shouldUseOptimizedApproach) {
    return findCommonSubstringsOptimized(validTexts);
  }

  // Original approach for smaller datasets
  return findCommonSubstringsOriginal(validTexts);
}

// Original O(n³) approach for small datasets with improved efficiency
function findCommonSubstringsOriginal(texts: string[]): string {
  const commonParts = new Set<string>();
  const firstText = texts[0];
  const maxLength = Math.min(firstText.length, 100);

  // Try substrings starting from longest possible to enable early termination
  for (let len = maxLength; len >= MIN_WORD_LENGTH; len--) {
    let foundAtThisLength = false;

    for (let i = 0; i <= firstText.length - len; i++) {
      const substring = firstText.slice(i, i + len);

      // Skip whitespace-only substrings or substrings with too much whitespace
      const trimmed = substring.trim();
      if (
        trimmed.length < MIN_WORD_LENGTH ||
        trimmed.length < substring.length * WHITESPACE_RATIO_THRESHOLD
      ) {
        continue;
      }

      // Check if this substring exists in all other texts
      if (texts.slice(1).every((text) => text.includes(substring))) {
        commonParts.add(substring);
        foundAtThisLength = true;

        // Smart skipping: skip overlapping positions for long substrings
        if (len > 15) {
          i += Math.min(3, Math.floor(len / 10)); // Conservative skipping
        }
      }
    }

    // Early termination: if we found good matches at this length, be more selective
    if (foundAtThisLength && commonParts.size >= 3) {
      // For very long substrings, stop searching shorter ones
      if (len > 30) break;
      // For medium length, continue but with higher threshold
      if (len > 15 && commonParts.size >= 5) break;
    }

    // Stop if we have enough matches
    if (commonParts.size >= 10) break;
  }

  // Convert to array and remove substrings contained within longer ones efficiently
  const partsArray = Array.from(commonParts);
  const filteredParts = removeContainedSubstrings(partsArray);

  // Sort by length (longest first) and join with spaces
  return filteredParts
    .sort((a, b) => b.length - a.length)
    .slice(0, 10)
    .join(" ")
    .trim();
}

// Optimized approach for large datasets using improved word and phrase matching
function findCommonSubstringsOptimized(texts: string[]): string {
  // Preprocess texts: normalize and create word mappings that preserve original casing
  const textData = texts.map((text) => {
    const words = text
      .split(/\s+/)
      .filter((word) => word.length >= MIN_WORD_LENGTH);
    const normalizedWords = words
      .map((word) => ({
        original: word,
        normalized: word.toLowerCase().replace(/[^\w@.-]/g, ""), // Preserve important chars
        startsAlphanumeric: /^[a-zA-Z0-9@.-]/.test(word), // Allow emails, URLs, and numbers
      }))
      .filter(
        (wordData) =>
          wordData.normalized.length >= MIN_WORD_LENGTH &&
          wordData.startsAlphanumeric
      );

    return {
      originalText: text,
      lowerText: text.toLowerCase(),
      words: normalizedWords,
      wordSet: new Set(normalizedWords.map((w) => w.normalized)),
      sentences: text
        .split(/[.!?]+/)
        .map((s) => s.trim())
        .filter((s) => s.length > 15),
    };
  });

  // Find common words using efficient Set intersection
  const wordSets = textData.map((data) => data.wordSet);
  const commonWordSet = intersectSets(wordSets);

  // Handle edge case where no common words exist
  if (commonWordSet.size === 0) {
    // Try character-based matching as fallback for very different texts
    return findCommonSubstringsOriginal(texts);
  }

  // Get original casing for common words from first text, with fallback handling
  const wordCaseMap = new Map<string, string>();
  if (textData.length > 0 && textData[0].words) {
    textData[0].words.forEach((wordData) => {
      if (commonWordSet.has(wordData.normalized)) {
        wordCaseMap.set(wordData.normalized, wordData.original);
      }
    });
  }

  const commonWords = Array.from(commonWordSet).map((word) => {
    const originalCase = wordCaseMap.get(word);
    if (originalCase) return originalCase;

    // Fallback: find the word in any of the original texts to preserve some casing
    for (const data of textData) {
      const found = data.words.find((w) => w.normalized === word);
      if (found) return found.original;
    }

    // Last resort: return normalized version (should rarely happen)
    return word;
  });

  // Find common phrases with preserved casing - now with fallback support
  const commonPhrases: string[] = [];

  // Always try phrase matching, with different limits based on text count
  const maxTextsForPhrases = textData.length <= 5 ? textData.length : 5;
  const relevantTextData = textData.slice(0, maxTextsForPhrases);

  if (relevantTextData.every((data) => data.sentences.length > 0)) {
    const firstSentences = relevantTextData[0].sentences.slice(
      0,
      MAX_SENTENCES_TO_PROCESS
    );
    const otherLowerTexts = relevantTextData
      .slice(1)
      .map((data) => data.lowerText);

    for (const sentence of firstSentences) {
      const words = sentence
        .split(/\s+/)
        .filter((word) => word.length >= MIN_WORD_LENGTH);

      // Look for phrases of MIN_PHRASE_WORDS-MAX_PHRASE_WORDS words with consistent word filtering
      for (
        let phraseLen = MIN_PHRASE_WORDS;
        phraseLen <= Math.min(MAX_PHRASE_WORDS, words.length);
        phraseLen++
      ) {
        for (let i = 0; i <= words.length - phraseLen; i++) {
          const phrase = words.slice(i, i + phraseLen).join(" ");
          const normalizedPhrase = phrase.toLowerCase();

          // Use consistent phrase length validation
          if (
            phrase.length < MIN_PHRASE_LENGTH ||
            phrase.length > MAX_PHRASE_LENGTH
          )
            continue;

          // Apply whitespace ratio check for consistency with original approach
          const trimmed = phrase.trim();
          if (trimmed.length < phrase.length * WHITESPACE_RATIO_THRESHOLD)
            continue;

          // Check if this phrase appears in other texts (case insensitive for consistency)
          if (
            otherLowerTexts.every((lowerText) =>
              lowerText.includes(normalizedPhrase)
            )
          ) {
            commonPhrases.push(phrase); // Keep original casing
          }
        }
      }

      // Stop early if we have enough phrases
      if (commonPhrases.length >= 10) break;
    }
  }

  // Combine phrases and words, prioritizing longer matches
  const allMatches = [...commonPhrases, ...commonWords]
    .filter((match) => match.length >= 3)
    .sort((a, b) => b.length - a.length)
    .slice(0, 12); // Slightly reduced limit

  // Remove contained substrings efficiently using helper function
  const filteredMatches = removeContainedSubstrings(allMatches);

  // Final result with consistent length limits
  const finalMatches = filteredMatches.slice(0, 8);

  // If we have very few matches and originally had common words, include some words as fallback
  if (finalMatches.length < 3 && commonWords.length > 0) {
    const additionalWords = commonWords
      .filter((word) => !finalMatches.some((match) => match.includes(word)))
      .slice(0, 5 - finalMatches.length);
    finalMatches.push(...additionalWords);
  }

  return finalMatches.join(" ").trim();
}
