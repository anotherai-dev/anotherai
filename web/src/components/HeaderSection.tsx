import React from "react";

type Props = {
  title: string;
  description: string;
  className?: string;
  rightComponent?: React.ReactNode;
};

export function HeaderSection(props: Props) {
  const { title, description, className, rightComponent } = props;

  return (
    <div className={`flex items-start justify-between ${className || ""}`}>
      <div className="flex-1">
        <h1 className="text-2xl font-semibold text-gray-900 mb-2">{title}</h1>
        <p className="text-sm text-gray-600">{description}</p>
      </div>
      {rightComponent && <div className="flex-shrink-0 ml-4">{rightComponent}</div>}
    </div>
  );
}
