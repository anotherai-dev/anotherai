import { AlertCircle, Ban, Clock, Server, Shield, Zap } from "lucide-react";

interface PageErrorProps {
  error: globalThis.Error | string | unknown;
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

function parseErrorInput(
  error: Error | string | unknown,
  depth = 0
): {
  title?: string;
  message: string;
} {
  // Prevent infinite recursion
  if (depth > 3) {
    return { message: "Error object too deeply nested" };
  }

  // Handle string errors
  if (typeof error === "string") {
    // Try to parse as JSON first
    try {
      const parsed = JSON.parse(error);
      return parseErrorInput(parsed, depth + 1);
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

    // Check for simple Error interface: {error: string}
    if (errorObj.error && typeof errorObj.error === "string") {
      return {
        message: errorObj.error,
      };
    }

    // Check for nested error field (other structures)
    if (errorObj.error && typeof errorObj.error === "object") {
      return parseErrorInput(errorObj.error, depth + 1);
    }

    // Check for details.message pattern
    if (errorObj.details && typeof errorObj.details === "object") {
      const details = errorObj.details as Record<string, unknown>;
      if (details.message && typeof details.message === "string") {
        return { message: details.message };
      }
    }

    // Fallback to safe JSON string
    try {
      return { message: JSON.stringify(error) };
    } catch {
      return { message: "[Complex Error Object]" };
    }
  }

  // Fallback for any other types
  return { message: String(error) || "An unknown error occurred." };
}

function getDescriptionColor(titleColor: string): string {
  const colorMap: Record<string, string> = {
    "text-red-800": "text-red-700",
    "text-orange-800": "text-orange-700",
    "text-yellow-800": "text-yellow-700",
    "text-purple-800": "text-purple-700",
    "text-blue-800": "text-blue-700",
  };
  return colorMap[titleColor] || "text-gray-700";
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

  // Check if this is an API error and format the title accordingly
  let isApiError = false;
  if (error && typeof error === "object") {
    interface ApiErrorStructure {
      statusCode?: number;
      code?: string;
      details?: {
        error_type?: string;
        code?: string;
        [key: string]: unknown;
      };
      isApiError?: boolean;
    }

    let apiError: ApiErrorStructure | null = null;
    const errorObj = error as Record<string, unknown>;

    // Handle Error objects created by createErrorFromResponse
    if (errorObj.isApiError) {
      isApiError = true;
      apiError = errorObj as ApiErrorStructure;
    }
    // Handle raw error objects from database (parsed JSON) - flat structure
    else if (errorObj.code || errorObj.status_code || errorObj.details) {
      isApiError = true;
      apiError = {
        statusCode: errorObj.status_code as number,
        code: errorObj.code as string,
        details: errorObj.details as ApiErrorStructure["details"],
      };
    }

    if (isApiError && apiError) {
      // Start with HTTP status code and colon
      const titleParts = [];
      if (apiError.statusCode) {
        titleParts.push(`HTTP ${apiError.statusCode}:`);
      }

      // Add error_type from details if available
      if (apiError.details?.error_type) {
        titleParts.push(apiError.details.error_type);
      }

      // Add details code in parentheses if available
      if (apiError.details?.code) {
        titleParts.push(`(${apiError.details.code})`);
      }

      // Add main error code in parentheses if available
      if (apiError.code) {
        titleParts.push(`(${apiError.code})`);
      }

      if (titleParts.length > 0) {
        title = titleParts.join(" ");
      }
    }
  }

  // Only apply categorization if it's not an API error
  if (
    !isApiError &&
    (lowerMessage.includes("max_tokens") ||
      lowerMessage.includes("token limit") ||
      lowerMessage.includes("tokens exceeded"))
  ) {
    icon = <Zap className="w-4 h-4" />;
    title = errorTitle || "Token Limit Exceeded";
    color = "text-orange-800";
    bgColor = "bg-orange-50";
    borderColor = "border-orange-200";
  } else if (!isApiError && (lowerMessage.includes("timeout") || lowerMessage.includes("timed out"))) {
    icon = <Clock className="w-4 h-4" />;
    title = errorTitle || "Request Timeout";
    color = "text-yellow-800";
    bgColor = "bg-yellow-50";
    borderColor = "border-yellow-200";
  } else if (!isApiError && (lowerMessage.includes("rate limit") || lowerMessage.includes("rate_limit"))) {
    icon = <Ban className="w-4 h-4" />;
    title = errorTitle || "Rate Limit Exceeded";
    color = "text-purple-800";
    bgColor = "bg-purple-50";
    borderColor = "border-purple-200";
  } else if (!isApiError && (lowerMessage.includes("server") || lowerMessage.includes("overload"))) {
    icon = <Server className="w-4 h-4" />;
    title = errorTitle || "Server Error";
    color = "text-red-800";
    bgColor = "bg-red-50";
    borderColor = "border-red-200";
  } else if (!isApiError && lowerMessage.includes("content") && lowerMessage.includes("moderation")) {
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
          <div className={`${errorDetails.color} flex-shrink-0 mt-0.5`}>{errorDetails.icon}</div>
          <div className="flex-1 min-w-0 max-w-full">
            <div className={`text-sm font-medium ${errorDetails.color} ${showDescription ? "mb-1" : ""} break-words`}>
              {errorDetails.title}
            </div>
          </div>
        </div>
        {showDescription && (
          <div
            className={`text-xs ${getDescriptionColor(errorDetails.color)} break-all overflow-hidden max-w-full`}
            style={{ wordBreak: "break-word" }}
          >
            {errorDetails.description}
          </div>
        )}
      </div>
    </div>
  );
}
