import { findCommonSubstrings } from '../stringMatchingUtils';

describe('findCommonSubstrings', () => {
  describe('Input validation', () => {
    it('returns empty string for empty array', () => {
      expect(findCommonSubstrings([])).toBe('');
    });

    it('returns empty string for null/undefined input', () => {
      expect(findCommonSubstrings(null as any)).toBe('');
      expect(findCommonSubstrings(undefined as any)).toBe('');
    });

    it('filters out null/undefined/short texts', () => {
      expect(findCommonSubstrings([null as any, undefined as any, 'ab', 'test text'])).toBe('test text');
    });

    it('returns original text for single valid text', () => {
      expect(findCommonSubstrings(['single text'])).toBe('single text');
    });

    it('returns empty string when no valid texts exist', () => {
      expect(findCommonSubstrings(['a', 'b', ''])).toBe('');
    });
  });

  describe('Basic substring matching', () => {
    it('finds common substrings in simple texts', () => {
      const result = findCommonSubstrings(['hello world', 'hello universe', 'hello there']);
      expect(result).toContain('hello');
    });

    it('finds multiple common substrings', () => {
      const texts = [
        'The quick brown fox jumps',
        'The quick red fox runs', 
        'The quick blue fox walks'
      ];
      const result = findCommonSubstrings(texts);
      expect(result).toContain('The quick');
    });

    it('handles exact matches', () => {
      const result = findCommonSubstrings(['same text', 'same text', 'same text']);
      expect(result).toBe('same text');
    });

    it('returns empty for completely different texts', () => {
      const result = findCommonSubstrings(['apple', 'zebra', 'music']);
      expect(result).toBe('');
    });
  });

  describe('Advanced pattern matching', () => {
    it('finds common phrases in longer texts', () => {
      const texts = [
        'This is a comprehensive test for finding common patterns in text analysis',
        'This is a detailed test for finding common patterns in data processing',
        'This is a thorough test for finding common patterns in algorithm testing'
      ];
      const result = findCommonSubstrings(texts);
      expect(result.length).toBeGreaterThan(0);
      expect(result).toContain('test for finding common patterns');
    });

    it('prioritizes longer matches over shorter ones', () => {
      const texts = [
        'machine learning algorithm',
        'machine learning model',
        'machine learning system'
      ];
      const result = findCommonSubstrings(texts);
      expect(result).toContain('machine learning');
    });

    it('handles nested substrings correctly', () => {
      const texts = [
        'artificial intelligence systems',
        'artificial intelligence tools',
        'artificial intelligence methods'
      ];
      const result = findCommonSubstrings(texts);
      expect(result).toContain('artificial intelligence');
    });
  });

  describe('Edge cases and whitespace handling', () => {
    it('handles texts with extra whitespace', () => {
      const texts = [
        '  hello   world  ',
        ' hello   world ',
        'hello world'
      ];
      const result = findCommonSubstrings(texts);
      expect(result).toContain('hello');
      expect(result).toContain('world');
    });

    it('skips whitespace-heavy substrings', () => {
      const texts = [
        'word1     word2',
        'word1     word3',
        'word1     word4'
      ];
      const result = findCommonSubstrings(texts);
      expect(result).toContain('word1');
    });

    it('handles special characters and punctuation', () => {
      const texts = [
        'user@example.com sent a message',
        'user@example.com received a reply',
        'user@example.com posted content'
      ];
      const result = findCommonSubstrings(texts);
      expect(result).toContain('user@example.com');
    });
  });

  describe('Performance optimizations', () => {
    it('uses optimized approach for large datasets', () => {
      const largeTexts = Array(15).fill(0).map((_, i) => 
        `This is test number ${i} with common patterns and shared vocabulary elements`
      );
      const result = findCommonSubstrings(largeTexts);
      expect(result).toContain('with common patterns');
      expect(result).toContain('shared vocabulary elements');
    });

    it('handles very long texts efficiently', () => {
      const longText = 'word '.repeat(2000) + 'common pattern here';
      const texts = [
        longText,
        'different start but common pattern here and more',
        'another beginning common pattern here at end'
      ];
      const result = findCommonSubstrings(texts);
      expect(result).toContain('common pattern here');
    });
  });

  describe('Word-based matching in optimized approach', () => {
    it('finds common words efficiently', () => {
      const texts = [
        'machine learning artificial intelligence',
        'deep learning artificial intelligence',
        'reinforcement learning artificial intelligence'
      ];
      const result = findCommonSubstrings(texts);
      expect(result).toContain('learning');
      expect(result).toContain('artificial');
      expect(result).toContain('intelligence');
    });

    it('preserves original casing', () => {
      const texts = [
        'OpenAI GPT Model',
        'OpenAI BERT Model',
        'OpenAI T5 Model'
      ];
      const result = findCommonSubstrings(texts);
      expect(result).toContain('OpenAI');
      expect(result).toContain('Model');
    });

    it('handles mixed case correctly', () => {
      const texts = [
        'JavaScript is great',
        'javascript is powerful',
        'JavaScript is useful'
      ];
      const result = findCommonSubstrings(texts);
      expect(result.length).toBeGreaterThan(0);
    });
  });

  describe('Phrase detection', () => {
    it('finds common phrases of appropriate length', () => {
      const texts = [
        'The quick brown fox jumps over the lazy dog every morning',
        'The quick brown fox runs over the lazy cat every evening',
        'The quick brown fox walks over the lazy bird every afternoon'
      ];
      const result = findCommonSubstrings(texts);
      expect(result).toContain('The quick brown fox');
    });

    it('respects phrase length limits', () => {
      const texts = [
        'very short phrase here and there',
        'very short phrase here and elsewhere', 
        'very short phrase here and anywhere'
      ];
      const result = findCommonSubstrings(texts);
      expect(result).toContain('very short phrase here');
    });
  });

  describe('Fallback behavior', () => {
    it('falls back to character-based matching when no common words exist', () => {
      const texts = [
        'abc123def456',
        'xyz123ghi456', 
        'rst123jkl456'
      ];
      const result = findCommonSubstrings(texts);
      expect(result).toContain('123');
      expect(result).toContain('456');
    });

    it('handles emoji and unicode characters', () => {
      const texts = [
        'Hello 👋 world 🌍',
        'Hello 👋 universe 🌌',
        'Hello 👋 earth 🌎'
      ];
      const result = findCommonSubstrings(texts);
      expect(result).toContain('Hello');
    });
  });

  describe('Result formatting and limits', () => {
    it('limits result length appropriately', () => {
      const texts = Array(10).fill(0).map((_, i) => 
        `common word${i} shared phrase${i} repeated pattern${i} test data${i}`
      );
      const result = findCommonSubstrings(texts);
      expect(result.length).toBeLessThan(500); // Reasonable length limit
    });

    it('joins results with spaces', () => {
      const texts = [
        'first common second common',
        'first shared second shared',
        'first pattern second pattern'
      ];
      const result = findCommonSubstrings(texts);
      expect(result.includes(' ')).toBeTruthy();
      expect(result.trim()).toBe(result); // No leading/trailing spaces
    });
  });
});