import { useEffect, useState } from "react";
import { ModelIconWithName } from "@/components/ModelIcon";

interface StickyHeaderData {
  versionNumber: number;
  modelId: string;
  reasoningEffort?: "disabled" | "low" | "medium" | "high";
  reasoningBudget?: number;
}

interface StickyTableHeadersProps {
  stickyHeaderData: StickyHeaderData[];
  columnWidth: number;
  scrollLeft: number;
  containerLeft: number;
  containerWidth: number;
  headerRef: React.RefObject<HTMLTableSectionElement>;
  tableRef: React.RefObject<HTMLTableElement>;
}

export function StickyTableHeaders({
  stickyHeaderData,
  columnWidth,
  scrollLeft,
  containerLeft,
  containerWidth,
  headerRef,
  tableRef,
}: StickyTableHeadersProps) {
  // State to track if headers are visible
  const [showStickyHeaders, setShowStickyHeaders] = useState(false);

  // Use intersection observer to detect when headers and table are visible
  useEffect(() => {
    if (!headerRef.current || !tableRef.current) return;

    let headerIntersecting = true;
    let tableIntersecting = true;

    const updateStickyHeaderVisibility = () => {
      // Show sticky headers only when:
      // 1. Headers are not visible (scrolled out of view)
      // 2. Table is still visible (not completely scrolled past)
      setShowStickyHeaders(!headerIntersecting && tableIntersecting);
    };

    const headerObserver = new IntersectionObserver(
      ([entry]) => {
        headerIntersecting = entry.isIntersecting;
        updateStickyHeaderVisibility();
      },
      {
        threshold: 0.1, // Trigger when less than 10% of headers are visible
      }
    );

    const tableObserver = new IntersectionObserver(
      ([entry]) => {
        tableIntersecting = entry.isIntersecting;
        updateStickyHeaderVisibility();
      },
      {
        threshold: 0.01, // Trigger when table is barely visible
      }
    );

    headerObserver.observe(headerRef.current);
    tableObserver.observe(tableRef.current);

    return () => {
      headerObserver.disconnect();
      tableObserver.disconnect();
    };
  }, [headerRef, tableRef]);

  if (!showStickyHeaders) {
    return null;
  }

  return (
    <div
      className="fixed top-0 z-30 pointer-events-none overflow-hidden border-l border-r border-gray-200"
      style={{
        left: containerLeft + 240, // Position after the sticky first column
        width: containerWidth - 240, // Take up remaining width
        height: "64px", // Height + shadow space
      }}
    >
      {/* Main header content */}
      <div className="bg-gray-50/90 backdrop-blur-sm border-b border-gray-200 h-[60px]">
        <div
          className="flex h-full"
          style={{
            transform: `translateX(-${scrollLeft}px)`, // Follow horizontal scroll
          }}
        >
          {stickyHeaderData.map((headerData, index) => (
            <div
              key={index}
              className="flex flex-col justify-center items-start border-r border-gray-200 last:border-r-0 flex-shrink-0"
              style={{
                width: `${columnWidth}px`,
                minWidth: `${columnWidth}px`,
                maxWidth: `${columnWidth}px`,
                paddingLeft: "16px", // px-4 = 16px
                paddingRight: "14px", // Further reduced to align borders
              }}
            >
              <div className="text-gray-800 font-semibold text-sm mb-1">Version {headerData.versionNumber}</div>
              <div className="px-2 py-1 text-xs rounded font-medium bg-gray-200 border border-gray-300 text-gray-900 w-fit">
                <ModelIconWithName
                  modelId={headerData.modelId}
                  size={12}
                  nameClassName="text-xs text-gray-900 font-medium"
                  reasoningEffort={headerData.reasoningEffort}
                  reasoningBudget={headerData.reasoningBudget}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
      {/* Bottom-only shadow using gradient */}
      <div
        className="w-full h-1"
        style={{
          background: "linear-gradient(to bottom, rgba(0, 0, 0, 0.05), transparent)",
        }}
      />
    </div>
  );
}
