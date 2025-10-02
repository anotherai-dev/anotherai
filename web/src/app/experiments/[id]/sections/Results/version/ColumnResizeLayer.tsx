import { ColumnResizer } from "./ColumnResizer";

interface ColumnResizeLayerProps {
  versionIds: string[];
  columnWidths: number[];
  onWidthChange: (versionId: string, width: number) => void;
  onResizeStart?: () => void;
  onResizeEnd?: () => void;
}

export function ColumnResizeLayer({
  versionIds,
  columnWidths,
  onWidthChange,
  onResizeStart,
  onResizeEnd,
}: ColumnResizeLayerProps) {
  if (versionIds.length === 0) return null;

  return (
    <>
      {versionIds.map((versionId, index) => {
        // Don't show resizer after the last column
        if (index === versionIds.length - 1) {
          return null;
        }

        const currentWidth = columnWidths[index] || 400;

        return (
          <div
            key={`resizer-${versionId}-${index}`}
            className="absolute top-0 bottom-0 pointer-events-none z-30"
            style={{
              // Position at the end of the current column (index + 1 because we skip the first sticky column)
              left: `calc(var(--column-${index + 1}-end, 0px))`,
            }}
          >
            <div className="pointer-events-auto">
              <ColumnResizer
                leftVersionId={versionId}
                rightVersionId={versionIds[index + 1]}
                leftInitialWidth={currentWidth}
                onWidthChange={onWidthChange}
                onResizeStart={onResizeStart}
                onResizeEnd={onResizeEnd}
              />
            </div>
          </div>
        );
      })}
    </>
  );
}
