import { cx } from "class-variance-authority";
import { HoverPopover } from "./HoverPopover";

type Props = {
  completionsLast3Days: number;
};

export function ActivityIndicator(props: Props) {
  const { completionsLast3Days } = props;
  const isActive = completionsLast3Days > 0;

  const indicator = (
    <div className="relative">
      <div className={cx("w-[6px] h-[6px] rounded-full", isActive ? "bg-green-500 animate-pulse" : "bg-gray-300")} />
      <div
        className={cx(
          "absolute top-[-3px] left-[-3px] w-[12px] h-[12px] rounded-full border",
          isActive ? "border-green-500 animate-pulse" : "border-gray-300"
        )}
      />
    </div>
  );

  if (isActive) {
    const popoverText =
      completionsLast3Days === 1 ? "1 completion in last 3 days" : `${completionsLast3Days} completions in last 3 days`;

    return (
      <HoverPopover content={popoverText} position="top" popoverClassName="bg-gray-800 rounded-[2px]">
        {indicator}
      </HoverPopover>
    );
  }

  return indicator;
}
