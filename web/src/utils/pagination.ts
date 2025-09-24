export interface PaginationInfo {
  hasPagination: boolean;
  pageSize: number;
  currentPage: number;
}

export interface PaginationParams {
  limit: number;
  offset: number;
}

/**
 * Detects if a SQL query contains pagination variables {limit} and {offset}
 */
export function detectPaginationVariables(query: string): boolean {
  const limitPattern = /\{limit\}/gi;
  const offsetPattern = /\{offset\}/gi;

  return limitPattern.test(query) && offsetPattern.test(query);
}

/**
 * Extracts pagination parameters from a SQL query with pagination variables
 * Returns the limit value if found, otherwise returns null
 */
export function extractLimitFromQuery(query: string): number | null {
  // Look for LIMIT followed by {limit} pattern
  const limitMatch = query.match(/LIMIT\s+\{limit\}/gi);
  if (!limitMatch) {
    // Fall back to regular LIMIT clause
    const regularLimitMatch = query.match(/LIMIT\s+(\d+)/gi);
    if (regularLimitMatch) {
      const limitValue = regularLimitMatch[0].match(/\d+/);
      return limitValue ? parseInt(limitValue[0], 10) : null;
    }
    return null;
  }

  // For pagination variables, we'll use a default page size
  return 20; // Default page size
}

/**
 * Replaces pagination variables in a SQL query with actual values
 */
export function replacePaginationVariables(query: string, params: PaginationParams): string {
  let result = query;

  // Replace {limit} with actual limit value
  result = result.replace(/\{limit\}/gi, params.limit.toString());

  // Replace {offset} with actual offset value
  result = result.replace(/\{offset\}/gi, params.offset.toString());

  return result;
}

/**
 * Calculates pagination parameters based on current page and page size
 */
export function calculatePaginationParams(currentPage: number, pageSize: number): PaginationParams {
  return {
    limit: pageSize,
    offset: (currentPage - 1) * pageSize,
  };
}

/**
 * Processes a SQL query for pagination, detecting variables and replacing them if necessary
 */
export function processPaginationQuery(
  query: string,
  currentPage: number = 1,
  pageSize: number = 20
): {
  processedQuery: string;
  hasPagination: boolean;
  paginationInfo: PaginationInfo;
} {
  const hasPagination = detectPaginationVariables(query);

  if (!hasPagination) {
    return {
      processedQuery: query,
      hasPagination: false,
      paginationInfo: {
        hasPagination: false,
        pageSize: 0,
        currentPage: 1,
      },
    };
  }

  // Use the provided pageSize parameter for pagination variables
  const finalPageSize = pageSize;

  const paginationParams = calculatePaginationParams(currentPage, finalPageSize);
  const processedQuery = replacePaginationVariables(query, paginationParams);

  return {
    processedQuery,
    hasPagination: true,
    paginationInfo: {
      hasPagination: true,
      pageSize: finalPageSize,
      currentPage,
    },
  };
}
