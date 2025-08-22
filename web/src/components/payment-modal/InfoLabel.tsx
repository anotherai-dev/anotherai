"use client";

interface InfoLabelProps {
  text: string;
}

export function InfoLabel({ text }: InfoLabelProps) {
  return (
    <div className="px-4 py-3 bg-blue-50 border-l-4 border-blue-400">
      <div className="text-[13px] text-blue-700">{text}</div>
    </div>
  );
}
