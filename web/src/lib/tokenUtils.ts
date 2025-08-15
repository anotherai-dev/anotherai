/**
 * Calculates the optimal refresh interval for a JWT token based on its expiry time.
 * Refreshes at 80% of token lifetime, with bounds between 5 minutes and 55 minutes.
 *
 * @param token - The JWT token to analyze
 * @returns The refresh interval in milliseconds
 */
export function calculateRefreshInterval(token: string | null): number {
  if (!token) return 55 * 60 * 1000; // Default 55 minutes

  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    const expiryTime = payload.exp * 1000; // Convert to milliseconds
    const currentTime = Date.now();
    const timeUntilExpiry = expiryTime - currentTime;

    // Refresh at 80% of token lifetime, but not less than 5 minutes or more than 55 minutes
    const refreshTime = Math.min(Math.max(timeUntilExpiry * 0.8, 5 * 60 * 1000), 55 * 60 * 1000);

    return Math.max(refreshTime, 60 * 1000); // Minimum 1 minute
  } catch {
    return 55 * 60 * 1000; // Fallback to 55 minutes
  }
}
