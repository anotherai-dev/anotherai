import { NextFetchEvent, NextRequest, NextResponse } from "next/server";
import { isClerkEnabled } from "@/lib/utils";

export default function middleware(request: NextRequest, event: NextFetchEvent) {
  // Only apply Clerk middleware if the publishable key is set
  if (isClerkEnabled()) {
    try {
      // Import Clerk middleware conditionally
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const { clerkMiddleware } = require("@clerk/nextjs/server");
      return clerkMiddleware()(request, event);
    } catch {
      // Clerk not available, fall through to default behavior
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
