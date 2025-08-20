"use client";

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
 * Wait for auth token to be available when Clerk is enabled
 */
async function waitForAuthToken(maxWaitMs = 5000): Promise<string | null> {
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  if (!clerkEnabled) {
    return null;
  }

  const startTime = Date.now();
  const checkInterval = 100; // Check every 100ms

  return new Promise((resolve) => {
    const checkToken = () => {
      const token = useAuthToken.getState().token;
      const elapsed = Date.now() - startTime;

      // If we have a valid, non-expired token or timeout exceeded, resolve
      if ((token && !isTokenExpired(token)) || elapsed >= maxWaitMs) {
        resolve(token);
        return;
      }

      // Continue waiting for valid token
      setTimeout(checkToken, checkInterval);
    };

    checkToken();
  });
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
  // Wait for token to be synced if Clerk is enabled
  const token = await waitForAuthToken();

  // Prepare headers
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  // Add Authorization header if we have a valid, non-expired token
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Make the request through Next.js API proxy
  return fetch(`/api${path}`, {
    ...options,
    headers,
  });
}
