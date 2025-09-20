import { ChevronLeft, ChevronRight } from "lucide-react";

interface SimplePaginationProps {
  currentPage: number;
  onPageChange: (page: number) => void;
  isLoading?: boolean;
  hasNextPage?: boolean; // Optional hint if we know there's a next page
}

export function SimplePagination({ currentPage, onPageChange, isLoading = false, hasNextPage }: SimplePaginationProps) {
  const handlePrevious = () => {
    if (currentPage > 1 && !isLoading) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNext = () => {
    if (!isLoading) {
      onPageChange(currentPage + 1);
    }
  };

  return (
    <div className="flex items-center justify-center px-4 py-3 bg-white border-t border-gray-200">
      <div className="flex items-center gap-4">
        <button
          onClick={handlePrevious}
          disabled={currentPage <= 1 || isLoading}
          className="flex items-center justify-center w-8 h-8 text-sm text-gray-700 border border-gray-300 rounded hover:bg-gray-50 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-2 text-sm text-gray-700">
          <span>Page</span>
          <span className="font-semibold">{currentPage}</span>
        </div>

        <button
          onClick={handleNext}
          disabled={isLoading || hasNextPage === false}
          className="flex items-center justify-center w-8 h-8 text-sm text-gray-700 border border-gray-300 rounded hover:bg-gray-50 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
