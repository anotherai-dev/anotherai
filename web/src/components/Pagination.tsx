import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationProps {
  currentPage: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  isLoading?: boolean;
}

export function Pagination({ currentPage, totalItems, pageSize, onPageChange, isLoading = false }: PaginationProps) {
  const totalPages = Math.ceil(totalItems / pageSize);

  if (totalPages <= 1) {
    return null;
  }

  const handlePrevious = () => {
    if (currentPage > 1 && !isLoading) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNext = () => {
    if (currentPage < totalPages && !isLoading) {
      onPageChange(currentPage + 1);
    }
  };

  const handlePageClick = (page: number) => {
    if (page !== currentPage && !isLoading) {
      onPageChange(page);
    }
  };

  // Generate page numbers to show
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    const maxVisiblePages = 5;

    if (totalPages <= maxVisiblePages) {
      // Show all pages if total is small
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Always show first page
      pages.push(1);

      if (currentPage > 3) {
        pages.push("...");
      }

      // Show pages around current page
      const start = Math.max(2, currentPage - 1);
      const end = Math.min(totalPages - 1, currentPage + 1);

      for (let i = start; i <= end; i++) {
        if (i !== 1 && i !== totalPages) {
          pages.push(i);
        }
      }

      if (currentPage < totalPages - 2) {
        pages.push("...");
      }

      // Always show last page
      if (totalPages > 1) {
        pages.push(totalPages);
      }
    }

    return pages;
  };

  const pageNumbers = getPageNumbers();

  return (
    <div className="flex items-center justify-center px-4 py-3 bg-white border-t border-gray-200">
      <div className="flex items-center gap-1">
        <button
          onClick={handlePrevious}
          disabled={currentPage <= 1 || isLoading}
          className="flex items-center justify-center w-8 h-8 text-sm text-gray-700 border border-gray-300 rounded hover:bg-gray-50 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-1 mx-2">
          {pageNumbers.map((page, index) =>
            page === "..." ? (
              <span key={`ellipsis-${index}`} className="px-2 py-1 text-sm text-gray-500">
                ...
              </span>
            ) : (
              <button
                key={page}
                onClick={() => handlePageClick(page as number)}
                disabled={isLoading}
                className={`flex items-center justify-center w-8 h-8 text-sm border rounded transition-colors cursor-pointer ${
                  currentPage === page
                    ? "bg-gray-600 text-white border-gray-600"
                    : "text-gray-700 border-gray-300 hover:bg-gray-50"
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {page}
              </button>
            )
          )}
        </div>

        <button
          onClick={handleNext}
          disabled={currentPage >= totalPages || isLoading}
          className="flex items-center justify-center w-8 h-8 text-sm text-gray-700 border border-gray-300 rounded hover:bg-gray-50 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
