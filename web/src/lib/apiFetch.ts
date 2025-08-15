"use client";

import { authLogger } from "@/lib/logger";
import { useAuthToken } from "@/store/authToken";

/**
 * Checks if a JWT token is expired
 */
function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    // Add 30 second buffer to avoid edge cases
    return payload.exp * 1000 < Date.now() + 30000;
  } catch {
    return true;
  }
}

/**
 * Client-side fetch function that calls a relative endpoint
 * Automatically includes Clerk authentication tokens from the Zustand auth store.
 *
 * @param path - The API path (will be prefixed with /api)
 * @param options - Standard fetch options
 * @returns Promise<Response>
 */
export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  // Get token from Zustand store
  const token = useAuthToken.getState().token;

  // Prepare headers
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  // Add Authorization header if we have a valid, non-expired token
  if (token && !isTokenExpired(token)) {
    headers["Authorization"] = `Bearer ${token}`;
  } else if (token && isTokenExpired(token)) {
    authLogger.warn("JWT token is expired, making request without Authorization header");
  }

  // Make the request through Next.js API proxy
  return fetch(`/api${path}`, {
    ...options,
    headers,
  });
}
