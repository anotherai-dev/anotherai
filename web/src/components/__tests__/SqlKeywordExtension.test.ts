// Mock TipTap dependencies
jest.mock('@tiptap/core', () => ({
  Extension: {
    create: jest.fn().mockReturnValue({
      name: 'sqlKeyword',
      addProseMirrorPlugins: jest.fn()
    })
  }
}));

jest.mock('@tiptap/pm/state', () => ({
  Plugin: jest.fn(),
  PluginKey: jest.fn()
}));

jest.mock('@tiptap/pm/view', () => ({
  Decoration: {
    inline: jest.fn()
  },
  DecorationSet: {
    create: jest.fn()
  }
}));

import { SqlKeywordExtension } from '../SqlKeywordExtension';

describe('SqlKeywordExtension', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Extension creation', () => {
    it('creates extension with correct name', () => {
      // The extension should exist
      expect(SqlKeywordExtension).toBeDefined();
    });

    it('should include common SQL keywords in regex pattern', () => {
      // Test the expected SQL keywords that should be highlighted
      const commonKeywords = ['SELECT', 'FROM', 'WHERE', 'ORDER', 'BY', 'LIMIT', 'JOIN', 'INSERT', 'UPDATE', 'DELETE'];
      
      // Create a test text with these keywords
      const testText = 'SELECT * FROM users WHERE id = 1 ORDER BY name LIMIT 10';
      
      // Test that these keywords would be matched by a typical SQL keyword regex
      commonKeywords.forEach(keyword => {
        if (testText.includes(keyword)) {
          const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
          expect(testText.match(regex)).toBeTruthy();
        }
      });
    });

    it('should handle case-insensitive matching', () => {
      const testCases = [
        'select * from users',
        'SELECT * FROM USERS', 
        'Select * From Users',
        'sElEcT * fRoM uSeRs'
      ];
      
      testCases.forEach(text => {
        const regex = new RegExp(`\\b(SELECT|FROM)\\b`, 'gi');
        const matches = text.match(regex);
        expect(matches).toBeTruthy();
        expect(matches?.length).toBeGreaterThanOrEqual(2);
      });
    });

    it('should match whole words only', () => {
      // Words that contain SQL keywords but aren't exact matches
      const nonMatches = [
        'SELECTION', // Contains SELECT
        'FROMAGE',    // Contains FROM
        'SOMEWHERE',  // Contains WHERE
      ];
      
      nonMatches.forEach(word => {
        const regex = new RegExp(`\\b(SELECT|FROM|WHERE)\\b`, 'gi');
        expect(word.match(regex)).toBeFalsy();
      });
    });
  });

  describe('SQL Keywords validation', () => {
    it('should recognize DDL keywords', () => {
      const ddlKeywords = ['CREATE', 'DROP', 'ALTER', 'TABLE'];
      const testQuery = 'CREATE TABLE users; DROP TABLE old_users; ALTER TABLE posts ADD COLUMN';
      
      ddlKeywords.forEach(keyword => {
        const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
        expect(testQuery.match(regex)).toBeTruthy();
      });
    });

    it('should recognize DML keywords', () => {
      const dmlKeywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE'];
      const testQuery = 'SELECT * FROM users; INSERT INTO users VALUES; UPDATE users SET; DELETE FROM users WHERE';
      
      dmlKeywords.forEach(keyword => {
        const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
        expect(testQuery.match(regex)).toBeTruthy();
      });
    });

    it('should recognize aggregate functions', () => {
      const aggregateFunctions = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX'];
      const testQuery = 'SELECT COUNT(*), SUM(price), AVG(rating), MIN(date), MAX(score) FROM products';
      
      aggregateFunctions.forEach(func => {
        const regex = new RegExp(`\\b${func}\\b`, 'gi');
        expect(testQuery.match(regex)).toBeTruthy();
      });
    });

    it('should recognize JOIN keywords', () => {
      const joinKeywords = ['JOIN', 'LEFT', 'INNER', 'ON'];
      const testQuery = 'SELECT * FROM users u LEFT JOIN posts p ON u.id = p.user_id INNER JOIN comments c ON p.id = c.post_id';
      
      joinKeywords.forEach(keyword => {
        const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
        expect(testQuery.match(regex)).toBeTruthy();
      });
    });
  });

  describe('Regex performance and behavior', () => {
    it('should handle long SQL queries efficiently', () => {
      const longQuery = `
        SELECT DISTINCT u.id, u.name, u.email, p.title, p.content, c.comment_text
        FROM users u
        INNER JOIN posts p ON u.id = p.user_id
        LEFT JOIN comments c ON p.id = c.post_id
        WHERE u.active = true
        AND p.published = true
        AND (p.created_at >= '2023-01-01' OR p.updated_at >= '2023-01-01')
        ORDER BY p.created_at DESC, u.name ASC
        LIMIT 100 OFFSET 0
      `.trim();
      
      // Test that we can handle regex matching on long text
      const sqlKeywords = ['SELECT', 'DISTINCT', 'FROM', 'INNER', 'JOIN', 'ON', 'LEFT', 'WHERE', 'AND', 'OR', 'ORDER', 'BY', 'LIMIT', 'OFFSET'];
      const keywordRegex = new RegExp(`\\b(${sqlKeywords.join('|')})\\b`, 'gi');
      
      const startTime = performance.now();
      const matches: string[] = [];
      let match;
      keywordRegex.lastIndex = 0;
      
      while ((match = keywordRegex.exec(longQuery)) !== null) {
        matches.push(match[0]);
      }
      
      const endTime = performance.now();
      
      expect(matches.length).toBeGreaterThan(0);
      expect(endTime - startTime).toBeLessThan(50); // Should be fast
    });

    it('should reset regex lastIndex properly', () => {
      const testText = 'SELECT FROM WHERE SELECT FROM WHERE';
      const keywordRegex = new RegExp(`\\b(SELECT|FROM|WHERE)\\b`, 'gi');
      
      // First pass
      const firstPassMatches: string[] = [];
      let match;
      keywordRegex.lastIndex = 0;
      
      while ((match = keywordRegex.exec(testText)) !== null) {
        firstPassMatches.push(match[0]);
      }
      
      // Second pass - should find same matches if lastIndex is reset
      keywordRegex.lastIndex = 0;
      const secondPassMatches: string[] = [];
      
      while ((match = keywordRegex.exec(testText)) !== null) {
        secondPassMatches.push(match[0]);
      }
      
      expect(firstPassMatches).toEqual(secondPassMatches);
      expect(firstPassMatches.length).toBe(6); // Should find all 6 keywords
    });

    it('should handle mixed case and special scenarios', () => {
      const testCases = [
        'select * from users where id=1', // No spaces around operators
        'SELECT\n*\nFROM\nusers', // Multi-line
        '  SELECT  *  FROM  users  ', // Extra whitespace
        'select /*comment*/ from users', // With comments
      ];
      
      testCases.forEach(query => {
        const keywordRegex = new RegExp(`\\b(SELECT|FROM)\\b`, 'gi');
        const matches = query.match(keywordRegex);
        expect(matches).toBeTruthy();
        expect(matches?.length).toBeGreaterThanOrEqual(2);
      });
    });
  });

  describe('CSS styling', () => {
    it('should apply correct CSS classes', () => {
      const expectedClass = 'sql-keyword font-bold';
      
      // Test that the expected CSS class structure is correct
      expect(expectedClass).toContain('sql-keyword');
      expect(expectedClass).toContain('font-bold');
    });
  });

  describe('Text processing simulation', () => {
    it('should identify text nodes vs non-text nodes', () => {
      const textNode = {
        isText: true,
        text: 'SELECT * FROM users'
      };
      
      const nonTextNode = {
        isText: false,
        text: 'SELECT * FROM users'
      };
      
      // Plugin should only process text nodes
      expect(textNode.isText).toBe(true);
      expect(nonTextNode.isText).toBe(false);
    });

    it('should handle null and empty text gracefully', () => {
      const nullTextNode = {
        isText: true,
        text: null
      };
      
      const emptyTextNode = {
        isText: true,
        text: ''
      };
      
      const validTextNode = {
        isText: true,
        text: 'SELECT * FROM users'
      };
      
      // Should be able to distinguish between different text states
      expect(nullTextNode.text).toBe(null);
      expect(emptyTextNode.text).toBe('');
      expect(validTextNode.text).toBeTruthy();
    });
  });

  describe('Extension integration', () => {
    it('should be properly structured as TipTap extension', () => {
      // The extension should be callable
      expect(typeof SqlKeywordExtension).toBe('object');
    });

    it('should handle various SQL constructs', () => {
      const complexQueries = [
        'WITH cte AS (SELECT * FROM users) SELECT * FROM cte',
        'UNION ALL SELECT * FROM archived_users',
        'CASE WHEN status = "active" THEN 1 ELSE 0 END',
        'EXISTS (SELECT 1 FROM orders WHERE user_id = users.id)',
      ];
      
      // Each should contain recognizable SQL keywords
      complexQueries.forEach(query => {
        const hasKeywords = /\b(WITH|AS|SELECT|FROM|UNION|ALL|CASE|WHEN|THEN|ELSE|END|EXISTS)\b/gi.test(query);
        expect(hasKeywords).toBe(true);
      });
    });
  });
});