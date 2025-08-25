"use client";

import React from "react";

interface DeploymentsBaseCellProps {
  children: React.ReactNode;
  className?: string;
}

export function DeploymentsBaseCell({ children, className = "" }: DeploymentsBaseCellProps) {
  return <div className={`text-[13px] ${className}`}>{children}</div>;
}
