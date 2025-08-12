import { Loader2 } from "lucide-react";

interface LoadingIndicatorProps {
  size?: number;
}

export function LoadingIndicator({ size = 36 }: LoadingIndicatorProps) {
  return <Loader2 size={size} className="animate-spin text-gray-300" />;
}
