import { LoadingIndicator } from "@/components/LoadingIndicator";

export function LoadingState() {
  return (
    <div className="h-full flex flex-col items-center text-center" style={{ paddingTop: "25%" }}>
      <LoadingIndicator />
    </div>
  );
}
