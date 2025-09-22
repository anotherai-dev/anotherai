import { cookies } from "next/headers";

/**
 * Server-side cookie reader that can be used in Server Components
 */
export async function getServerSideCookie<T>(cookieName: string, defaultValue: T): Promise<T> {
  try {
    const cookieStore = await cookies();
    const cookie = cookieStore.get(cookieName);

    if (cookie?.value) {
      return JSON.parse(decodeURIComponent(cookie.value));
    }
  } catch (error) {
    console.error(`Error reading server-side cookie ${cookieName}:`, error);
  }

  return defaultValue;
}
