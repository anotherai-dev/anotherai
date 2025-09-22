"use client";

import { useCallback, useState } from "react";

// Helper function to parse cookies from string (works server-side too)
function parseCookieString(cookieString: string): Record<string, string> {
  const cookies: Record<string, string> = {};

  if (!cookieString) return cookies;

  cookieString.split(";").forEach((cookie) => {
    const [name, value] = cookie.trim().split("=");
    if (name && value) {
      try {
        cookies[name] = decodeURIComponent(value);
      } catch (error) {
        console.warn(`Error parsing cookie ${name}:`, error);
      }
    }
  });

  return cookies;
}

// Helper to get cookie value that works both server and client side
function getCookieValue<T>(cookieName: string, defaultValue: T): T {
  try {
    let cookieString = "";

    // Server side - check if we have access to cookies through headers
    if (typeof document === "undefined") {
      // This will work if we're in a component that has access to cookies
      // For now, just return default to prevent hydration mismatch
      return defaultValue;
    }

    // Client side
    cookieString = document.cookie;

    const cookies = parseCookieString(cookieString);
    const value = cookies[cookieName];

    if (value !== undefined) {
      return JSON.parse(value);
    }
  } catch (error) {
    console.error(`Error reading cookie ${cookieName}:`, error);
  }

  return defaultValue;
}

/**
 * A hook that provides state management with cookie persistence
 * This allows server-side access to the value, preventing hydration mismatches
 */
export function useCookieState<T>(
  cookieName: string,
  defaultValue: T,
  options?: {
    maxAge?: number; // Cookie expiration in seconds (default: 1 year)
    path?: string; // Cookie path (default: '/')
    secure?: boolean; // Only send over HTTPS
    sameSite?: "lax" | "strict" | "none";
  }
): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => {
    // On client-side, read from cookie. On server-side, use the passed defaultValue
    if (typeof document === "undefined") {
      return defaultValue;
    }
    return getCookieValue(cookieName, defaultValue);
  });

  // Set cookie with the new value
  const setCookieValue = useCallback(
    (newValue: T) => {
      setValue(newValue);

      if (typeof document === "undefined") {
        return;
      }

      try {
        const {
          maxAge = 365 * 24 * 60 * 60, // 1 year default
          path = "/",
          secure = false,
          sameSite = "lax",
        } = options || {};

        const cookieValue = encodeURIComponent(JSON.stringify(newValue));
        const cookieOptions = [
          `${cookieName}=${cookieValue}`,
          `path=${path}`,
          `max-age=${maxAge}`,
          `samesite=${sameSite}`,
          secure ? "secure" : "",
        ]
          .filter(Boolean)
          .join("; ");

        document.cookie = cookieOptions;
      } catch (error) {
        console.error(`Error setting cookie ${cookieName}:`, error);
      }
    },
    [cookieName, options]
  );

  return [value, setCookieValue];
}
