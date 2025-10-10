"use client";

import { Copy } from "lucide-react";
import { useToast } from "@/components/ToastProvider";

interface CopyButtonProps {
  text: string;
}

export function CopyButton({ text }: CopyButtonProps) {
  const { showToast } = useToast();

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(text);
      showToast("Copied to clipboard");
    } catch {
      showToast("Failed to copy");
    }
  };

  return (
    <button
      onClick={copyToClipboard}
      className="absolute top-2 right-2 p-1.5 bg-white hover:bg-gray-50 border border-gray-300 rounded text-xs text-gray-600 hover:text-gray-800 opacity-0 group-hover:opacity-100 transition-opacity z-10 cursor-pointer"
      title="Copy to clipboard"
    >
      <Copy size={12} />
    </button>
  );
}
