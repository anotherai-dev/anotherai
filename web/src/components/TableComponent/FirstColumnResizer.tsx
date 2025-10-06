interface FirstColumnResizerProps {
  width: number;
  onWidthChange: (width: number) => void;
}

export function FirstColumnResizer({ width, onWidthChange }: FirstColumnResizerProps) {
  return (
    <div
      style={{
        position: "absolute",
        right: "-16px",
        top: 0,
        bottom: 0,
        width: "4px",
        cursor: "col-resize",
        zIndex: 20,
        transform: "translateX(-16px)", // Move left by 16px to account for padding
      }}
      className="group"
      onMouseDown={(e) => {
        e.preventDefault();
        e.stopPropagation();

        const startX = e.clientX;
        const startWidth = width;

        const handleMouseMove = (e: MouseEvent) => {
          const deltaX = e.clientX - startX;
          const newWidth = Math.max(200, startWidth + deltaX);
          onWidthChange(newWidth);
        };

        const handleMouseUp = () => {
          document.removeEventListener("mousemove", handleMouseMove);
          document.removeEventListener("mouseup", handleMouseUp);
        };

        document.addEventListener("mousemove", handleMouseMove);
        document.addEventListener("mouseup", handleMouseUp);
      }}
    >
      {/* Wider hover area for easier grabbing */}
      <div className="absolute top-0 bottom-0 -left-3 -right-3" />

      {/* Visual indicator */}
      <div
        className="absolute top-0 bottom-0 w-0.5 bg-transparent group-hover:bg-blue-500 transition-colors"
        style={{ left: "50%", transform: "translateX(-50%)" }}
      />
    </div>
  );
}
