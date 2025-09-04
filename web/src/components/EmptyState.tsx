"use client";

import { ExternalLink } from "lucide-react";

interface EmptyStateProps {
  title: string;
  subtitle?: string;
  documentationUrl?: string;
  buttonText?: string;
}

export function EmptyState({ title, subtitle, documentationUrl, buttonText = "View Documentation" }: EmptyStateProps) {
  return (
    <div className="h-full flex flex-col items-center text-center" style={{ paddingTop: "25%" }}>
      <p className="text-gray-500 mb-1">{title}</p>
      {subtitle && <p className="text-gray-400 text-sm mb-4">{subtitle}</p>}
      {documentationUrl && (
        <button
          onClick={() => window.open(documentationUrl, "_blank", "noopener,noreferrer")}
          className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer px-2.5 py-1.5 rounded-[2px] text-[13px] shadow-sm shadow-black/5 inline-flex items-center gap-2"
        >
          <ExternalLink className="w-4 h-4" />
          {buttonText}
        </button>
      )}
    </div>
  );
}
