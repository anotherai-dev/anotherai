"use client";

import { cn } from "@/lib/utils";

interface CircularProgressProps {
  value: number; // Progress value from 0 to 100
  warning?: boolean; // Whether to show warning state (red color)
  size?: number; // Size of the circle in pixels
  strokeWidth?: number; // Width of the progress stroke
  className?: string;
}

export function CircularProgress({
  value,
  warning = false,
  size = 24,
  strokeWidth = 2.5,
  className,
}: CircularProgressProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (value / 100) * circumference;

  return (
    <div
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          className="text-gray-200"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className={cn("transition-all duration-300 ease-in-out", warning ? "text-red-500" : "text-blue-500")}
        />
      </svg>
    </div>
  );
}
