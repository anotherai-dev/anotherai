import { Allotment } from "allotment";
import "allotment/dist/style.css";
import { cx } from "class-variance-authority";
import { useCallback } from "react";
import React from "react";
import { useDebounceCallback, useLocalStorage } from "usehooks-ts";

type PersistantAllotmentProps = {
  name: string;
  initialSize: number[];
  className?: string;
  children: React.ReactNode;
  isAllotmentEnabled?: boolean;
};

export function PersistantAllotment(props: PersistantAllotmentProps) {
  const { name, initialSize, children, className, isAllotmentEnabled = true } = props;

  const [allotmentSizes, setAllotmentSizes] = useLocalStorage<number[]>(name, initialSize);

  const onAllotmentChange = useDebounceCallback(
    useCallback(
      (sizes: number[]) => {
        setAllotmentSizes(sizes);
      },
      [setAllotmentSizes]
    ),
    1000
  );

  if (!isAllotmentEnabled) {
    return (
      <div className={cx(className, "flex flex-row flex-1 h-full w-full")}>
        {React.Children.map(children, (child) => (
          <div className="flex-1">{child}</div>
        ))}
      </div>
    );
  }

  return (
    <Allotment defaultSizes={allotmentSizes} onChange={onAllotmentChange} className={className} separator={false}>
      {children}
    </Allotment>
  );
}
