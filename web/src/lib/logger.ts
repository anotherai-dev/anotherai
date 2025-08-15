/**
 * Production-safe logger for authentication and other sensitive operations
 */
const isDevelopment = process.env.NODE_ENV === "development";

interface LogMetadata {
  [key: string]: unknown;
}

export const authLogger = {
  info: (message: string, metadata?: LogMetadata) => {
    if (isDevelopment) {
      console.log(`[AUTH] ${message}`, metadata);
    }
  },

  warn: (message: string, error?: unknown) => {
    if (isDevelopment) {
      console.warn(`[AUTH WARNING] ${message}`, error);
    } else {
      // In production, log only non-sensitive error info
      console.warn(`[AUTH WARNING] ${message}`);
    }
  },

  error: (message: string, error?: unknown) => {
    if (isDevelopment) {
      console.error(`[AUTH ERROR] ${message}`, error);
    } else {
      // In production, log only the message without potentially sensitive error details
      console.error(`[AUTH ERROR] ${message}`);
    }
  },

  debug: (message: string, metadata?: LogMetadata) => {
    if (isDevelopment) {
      console.log(`[AUTH DEBUG] ${message}`, metadata);
    }
    // Never log debug info in production
  },
};
