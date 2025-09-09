import { useEffect, useRef, useState } from "react";

export function useScrollbarPositioning() {
  const [containerWidth, setContainerWidth] = useState(0);
  const [containerLeft, setContainerLeft] = useState(0);
  const [containerBottom, setContainerBottom] = useState(0);
  const [isHovering, setIsHovering] = useState(false);
  const hoverTimeoutRef = useRef<NodeJS.Timeout>();
  const containerRef = useRef<HTMLDivElement>(null);

  // Check if table bottom is visible in viewport
  const isTableBottomVisible =
    typeof window !== "undefined" && containerBottom <= window.innerHeight && containerBottom > 0;

  // Measure container dimensions and position
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setContainerWidth(containerRef.current.offsetWidth);
        setContainerLeft(rect.left);
        setContainerBottom(rect.bottom);
      }
    };

    // Use a timeout to ensure the DOM has rendered
    const timeoutId = setTimeout(updateDimensions, 0);

    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    window.addEventListener("scroll", updateDimensions);

    return () => {
      clearTimeout(timeoutId);
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }
      window.removeEventListener("resize", updateDimensions);
      window.removeEventListener("scroll", updateDimensions);
    };
  }, []);

  // Update dimensions continuously while hovering with 200ms interval
  useEffect(() => {
    if (!isHovering) return;

    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setContainerWidth(containerRef.current.offsetWidth);
        setContainerLeft(rect.left);
        setContainerBottom(rect.bottom);
      }
    };

    // Update immediately when hovering starts
    updateDimensions();

    // Set up interval to update dimensions while hovering
    const intervalId = setInterval(updateDimensions, 200); // Update every 200ms while hovering

    return () => {
      clearInterval(intervalId);
    };
  }, [isHovering]);

  const handleMouseEnter = () => {
    // Clear any pending hide timeout
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }

    setIsHovering(true);
    // Update dimensions when hovering starts
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setContainerWidth(containerRef.current.offsetWidth);
      setContainerLeft(rect.left);
      setContainerBottom(rect.bottom);
    }
  };

  const handleMouseLeave = () => {
    // Delay hiding to prevent flickering when moving between table elements
    hoverTimeoutRef.current = setTimeout(() => {
      setIsHovering(false);
    }, 100);
  };

  return {
    containerRef,
    containerWidth,
    containerLeft,
    containerBottom,
    isHovering,
    isTableBottomVisible,
    handleMouseEnter,
    handleMouseLeave,
    hoverTimeoutRef,
  };
}
