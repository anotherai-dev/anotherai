"use client";

import { KeyRound } from "lucide-react";

interface ApiKeysButtonProps {
  onClick: () => void;
  className?: string;
}

export function ApiKeysButton({ onClick, className }: ApiKeysButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-3 px-3 py-2 rounded-[4px] text-sm transition-colors mb-[2px] text-gray-700 hover:bg-gray-100 w-full text-left cursor-pointer ${className || ""}`}
    >
      <KeyRound className="w-4 h-4" />
      API Keys
    </button>
  );
}