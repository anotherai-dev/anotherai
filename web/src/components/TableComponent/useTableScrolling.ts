import { useEffect, useRef, useState } from "react";

interface UseTableScrollingProps {
  onScrollChange?: (scrollLeft: number) => void;
}

export function useTableScrolling(props?: UseTableScrollingProps) {
  // Container dimensions and positioning
  const [containerWidth, setContainerWidth] = useState(0);
  const [containerLeft, setContainerLeft] = useState(0);
  const [containerBottom, setContainerBottom] = useState(0);
  const [isHovering, setIsHovering] = useState(false);
  const [isScrolling, setIsScrolling] = useState(false);

  // Scroll position state
  const [scrollLeft, setScrollLeft] = useState(0);

  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const topScrollRef = useRef<HTMLDivElement>(null);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const scrollTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const lastScrollUpdateRef = useRef<{ source: "main" | "top"; timestamp: number } | null>(null);

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

    // Optimized scroll handler for better responsiveness
    const handleWindowScroll = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        // Only update the position-related values during scroll for better performance
        setContainerLeft(rect.left);
        setContainerBottom(rect.bottom);
      }
    };

    // Use a timeout to ensure the DOM has rendered
    const timeoutId = setTimeout(updateDimensions, 0);

    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    window.addEventListener("scroll", handleWindowScroll, { passive: true });

    return () => {
      clearTimeout(timeoutId);
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
      window.removeEventListener("resize", updateDimensions);
      window.removeEventListener("scroll", handleWindowScroll);
    };
  }, []);

  // Update dimensions continuously with 200ms interval (always, not just while hovering)
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setContainerWidth(containerRef.current.offsetWidth);
        setContainerLeft(rect.left);
        setContainerBottom(rect.bottom);
      }
    };

    // Set up interval to continuously update dimensions for scrollbar positioning
    const intervalId = setInterval(updateDimensions, 200); // Update every 200ms always

    return () => {
      clearInterval(intervalId);
    };
  }, []); // No dependency on isHovering - runs always

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

  const handleScroll = () => {
    // Show scrollbar during scroll events
    setIsScrolling(true);

    // Clear any existing scroll timeout
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }

    // Hide scrollbar after scroll ends (with delay)
    scrollTimeoutRef.current = setTimeout(() => {
      setIsScrolling(false);
    }, 1000); // Keep visible for 1 second after scrolling stops

    // Update dimensions during scroll
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setContainerWidth(containerRef.current.offsetWidth);
      setContainerLeft(rect.left);
      setContainerBottom(rect.bottom);
    }
  };

  // Sync scroll positions between top and main scroll areas
  const handleMainScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const now = Date.now();
    const lastUpdate = lastScrollUpdateRef.current;

    // If this scroll event was triggered by a programmatic update from the top scroll, ignore it
    if (lastUpdate && lastUpdate.source === "top" && now - lastUpdate.timestamp < 50) {
      return;
    }

    const newScrollLeft = e.currentTarget.scrollLeft;

    // Always call the callback immediately for synchronous CSS updates
    props?.onScrollChange?.(newScrollLeft);

    // Update React state (can be slower, used as fallback)
    setScrollLeft(newScrollLeft);

    // Mark that we're updating from the main scroll
    lastScrollUpdateRef.current = { source: "main", timestamp: now };

    if (topScrollRef.current && topScrollRef.current.scrollLeft !== newScrollLeft) {
      topScrollRef.current.scrollLeft = newScrollLeft;
    }

    handleScroll(); // Show scrollbar when scrolling occurs
  };

  const handleTopScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const now = Date.now();
    const lastUpdate = lastScrollUpdateRef.current;

    // If this scroll event was triggered by a programmatic update from the main scroll, ignore it
    if (lastUpdate && lastUpdate.source === "main" && now - lastUpdate.timestamp < 50) {
      return;
    }

    const newScrollLeft = e.currentTarget.scrollLeft;

    // Always call the callback immediately for synchronous CSS updates
    props?.onScrollChange?.(newScrollLeft);

    // Update React state (can be slower, used as fallback)
    setScrollLeft(newScrollLeft);

    // Mark that we're updating from the top scroll
    lastScrollUpdateRef.current = { source: "top", timestamp: now };

    if (scrollRef.current && scrollRef.current.scrollLeft !== newScrollLeft) {
      scrollRef.current.scrollLeft = newScrollLeft;
    }

    handleScroll(); // Show scrollbar when scrolling occurs
  };

  return {
    // Container positioning
    containerRef,
    containerWidth,
    containerLeft,
    containerBottom,
    isHovering,
    isScrolling,
    isTableBottomVisible,

    // Scroll refs and state
    scrollRef,
    topScrollRef,
    scrollLeft,

    // Event handlers
    handleMouseEnter,
    handleMouseLeave,
    handleScroll,
    handleMainScroll,
    handleTopScroll,

    // Timeout refs for cleanup
    hoverTimeoutRef,
    scrollTimeoutRef,
  };
}
