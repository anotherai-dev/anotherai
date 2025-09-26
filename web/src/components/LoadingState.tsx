import { LoadingIndicator } from "@/components/LoadingIndicator";

interface LoadingStateProps {
  padding?: boolean;
}

export function LoadingState({ padding = true }: LoadingStateProps) {
  return (
    <div className="h-full flex flex-col items-center text-center" style={padding ? { paddingTop: "25%" } : undefined}>
      <LoadingIndicator />
    </div>
  );
}
