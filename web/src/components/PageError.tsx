import { AlertCircle, Ban, Clock, Server, Shield, Zap } from "lucide-react";
import { Error } from "@/types/models";

interface PageErrorProps {
  error: Error | string;
  showDescription?: boolean;
  fitWidth?: boolean;
}

interface ErrorDetails {
  icon: React.ReactNode;
  title: string;
  description: string;
  color: string;
  bgColor: string;
  borderColor: string;
}

function parseErrorInput(error: Error | string | unknown): {
  title?: string;
  message: string;
} {
  // Handle string errors
  if (typeof error === "string") {
    // Try to parse as JSON first
    try {
      const parsed = JSON.parse(error);
      return parseErrorInput(parsed);
    } catch {
      // Not JSON, return as-is
      return { message: error };
    }
  }

  // Handle object errors
  if (error && typeof error === "object") {
    const errorObj = error as Record<string, unknown>;

    // Check for common error object patterns
    if (errorObj.message && typeof errorObj.message === "string") {
      return {
        title: errorObj.title && typeof errorObj.title === "string" ? errorObj.title : undefined,
        message: errorObj.message,
      };
    }

    // Check for nested error field
    if (errorObj.error) {
      return parseErrorInput(errorObj.error);
    }

    // Check for details.message pattern
    if (errorObj.details && typeof errorObj.details === "object") {
      const details = errorObj.details as Record<string, unknown>;
      if (details.message && typeof details.message === "string") {
        return { message: details.message };
      }
    }

    // Fallback to JSON string
    return { message: JSON.stringify(error) };
  }

  // Fallback for any other types
  return { message: String(error) || "An unknown error occurred." };
}

function getErrorDetails(error: Error | string | unknown): ErrorDetails {
  const { title: errorTitle, message } = parseErrorInput(error);
  const lowerMessage = message.toLowerCase();

  // Use provided title or categorize based on message content
  let title = errorTitle || "Error";
  let icon = <AlertCircle className="w-4 h-4" />;
  let color = "text-red-800";
  let bgColor = "bg-red-50";
  let borderColor = "border-red-200";

  if (lowerMessage.includes("max_tokens") || lowerMessage.includes("token")) {
    icon = <Zap className="w-4 h-4" />;
    title = errorTitle || "Token Limit Exceeded";
    color = "text-orange-800";
    bgColor = "bg-orange-50";
    borderColor = "border-orange-200";
  } else if (lowerMessage.includes("timeout") || lowerMessage.includes("timed out")) {
    icon = <Clock className="w-4 h-4" />;
    title = errorTitle || "Request Timeout";
    color = "text-yellow-800";
    bgColor = "bg-yellow-50";
    borderColor = "border-yellow-200";
  } else if (lowerMessage.includes("rate limit") || lowerMessage.includes("rate_limit")) {
    icon = <Ban className="w-4 h-4" />;
    title = errorTitle || "Rate Limit Exceeded";
    color = "text-purple-800";
    bgColor = "bg-purple-50";
    borderColor = "border-purple-200";
  } else if (lowerMessage.includes("server") || lowerMessage.includes("overload")) {
    icon = <Server className="w-4 h-4" />;
    title = errorTitle || "Server Error";
    color = "text-red-800";
    bgColor = "bg-red-50";
    borderColor = "border-red-200";
  } else if (lowerMessage.includes("content") && lowerMessage.includes("moderation")) {
    icon = <Shield className="w-4 h-4" />;
    title = errorTitle || "Content Moderation";
    color = "text-blue-800";
    bgColor = "bg-blue-50";
    borderColor = "border-blue-200";
  }

  return {
    icon,
    title,
    description: message,
    color,
    bgColor,
    borderColor,
  };
}

export function PageError({ error, showDescription = true, fitWidth = false }: PageErrorProps) {
  const errorDetails = getErrorDetails(error);

  return (
    <div
      className={`${errorDetails.bgColor} border ${errorDetails.borderColor} rounded-[2px] p-2 ${fitWidth ? "w-fit max-w-xs" : "w-0 min-w-full max-w-full"}`}
    >
      <div className="flex flex-col min-w-0 max-w-full">
        <div className="flex items-start gap-2 min-w-0 max-w-full">
          <div className={`${errorDetails.color} mt-0.5 flex-shrink-0`}>{errorDetails.icon}</div>
          <div className="flex-1 min-w-0 max-w-full overflow-hidden">
            <div className={`text-sm font-medium ${errorDetails.color} ${showDescription ? "mb-1" : ""} truncate`}>
              {errorDetails.title}
            </div>
          </div>
        </div>
        {showDescription && (
          <div
            className={`text-xs ${errorDetails.color.replace("800", "700")} break-all overflow-hidden max-w-full`}
            style={{ wordBreak: "break-word" }}
          >
            {errorDetails.description}
          </div>
        )}
      </div>
    </div>
  );
}
