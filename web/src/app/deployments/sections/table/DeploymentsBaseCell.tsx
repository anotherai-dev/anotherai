"use client";

import { memo } from "react";

interface DeploymentsBaseCellProps {
  children: React.ReactNode;
  className?: string;
}

function DeploymentsBaseCell({ children, className = "" }: DeploymentsBaseCellProps) {
  return <div className={`text-[13px] ${className}`}>{children}</div>;
}

export default memo(DeploymentsBaseCell);
