import { AlertCircle } from "lucide-react";
import React, { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class TableCellErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("TableCell Error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex items-center gap-1 px-2 py-1 text-xs text-red-600 bg-red-50 rounded-[2px] border border-red-200">
          <AlertCircle className="w-3 h-3 flex-shrink-0" />
          <span className="truncate">Error rendering cell</span>
        </div>
      );
    }

    return this.props.children;
  }
}
