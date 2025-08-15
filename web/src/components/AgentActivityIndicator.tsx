import { cn } from "@/lib/cn";

type Props = {
  isActive: boolean;
};

export function AgentActivityIndicator(props: Props) {
  const { isActive } = props;

  return (
    <div className="relative">
      <div className={cn("w-[6px] h-[6px] rounded-full", isActive ? "bg-green-500 animate-pulse" : "bg-gray-300")} />
      <div
        className={cn(
          "absolute top-[-3px] left-[-3px] w-[12px] h-[12px] rounded-full border",
          isActive ? "border-green-500 animate-pulse" : "border-gray-300"
        )}
      />
    </div>
  );
}
