"use server";

// eslint-disable-next-line no-restricted-imports
import { auth, clerkMiddleware } from "@clerk/nextjs/server";

export const middleware = clerkMiddleware();

export async function getToken() {
  const { getToken } = await auth();
  return getToken();
}
