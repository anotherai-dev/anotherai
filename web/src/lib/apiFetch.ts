"use client";

/**
 * Client-side fetch function that calls a relative endpoint
 * Automatically includes Clerk authentication tokens from the Zustand auth store.
 *
 * @param url - The URL to fetch (can be relative to API_BASE_URL or absolute)
 * @param options - Standard fetch options
 * @returns Promise<Response>
 */
export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  // Prepare headers
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  // Token will be handled backend side
  // Make the request through Next.js API proxy
  return fetch(`/api${path}`, {
    ...options,
    headers,
  });
}
