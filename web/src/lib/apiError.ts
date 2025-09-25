interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    status_code: number;
    details?: Record<string, unknown>;
    incur_cost?: boolean;
  };
}

export async function createErrorFromResponse(response: Response): Promise<Error> {
  const statusText = `${response.status} ${response.statusText}`;

  try {
    const errorBody = await response.json();

    // Handle the nested error structure
    if (errorBody.error && typeof errorBody.error === "object") {
      const apiError = errorBody as ApiErrorResponse;
      const { code, message, status_code, details } = apiError.error;

      // Use only the message without adding code prefix
      const errorMessage = message || statusText;

      // Create error object without triggering console logging
      const error = Object.create(Error.prototype);
      error.name = "ApiError";
      error.message = errorMessage;

      // Attach additional properties for debugging
      Object.assign(error, {
        code,
        statusCode: status_code || response.status,
        details,
        isApiError: true,
      });

      return error;
    }

    // Handle simple error structure
    if (errorBody.error && typeof errorBody.error === "string") {
      return new Error(errorBody.error);
    }

    // Handle message field
    if (errorBody.message) {
      return new Error(errorBody.message);
    }

    // Fallback to status if no recognizable error structure
    return new Error(`HTTP ${statusText}`);
  } catch {
    // If we can't parse the response body, fall back to status text
    return new Error(`HTTP ${statusText}`);
  }
}
