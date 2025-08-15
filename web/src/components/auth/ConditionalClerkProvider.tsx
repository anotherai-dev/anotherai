"use client";

import Image from "next/image";
import { ReactNode, useEffect, useMemo, useState } from "react";
import { getAuthStrategy } from "@/lib/authStrategy";
import { authLogger } from "@/lib/logger";
import { calculateRefreshInterval } from "@/lib/tokenUtils";
import { useAuthToken } from "@/store/authToken";

interface ClerkComponents {
  ClerkProvider: React.ComponentType<{
    publishableKey: string;
    signInFallbackRedirectUrl?: string;
    afterSignOutUrl?: string;
    signInUrl?: string;
    signUpUrl?: string;
    children: ReactNode;
  }>;
  SignedIn: React.ComponentType<{ children: ReactNode }>;
  SignedOut: React.ComponentType<{ children: ReactNode }>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  SignInButton: React.ComponentType<any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  SignUpButton: React.ComponentType<any>;
  UserButton: React.ComponentType<{ afterSignOutUrl?: string }>;
  useAuth: () => {
    isLoaded: boolean;
    isSignedIn: boolean | undefined;
    getToken: (options?: { template?: string }) => Promise<string | null>;
  };
  useUser: () => { isSignedIn: boolean | undefined };
}

export function ConditionalClerkProvider({ children }: { children: ReactNode }) {
  const authStrategy = useMemo(() => getAuthStrategy(), []);
  const [clerkComponents, setClerkComponents] = useState<ClerkComponents | null>(null);
  const [isLoading, setIsLoading] = useState(authStrategy.name === "clerk");
  const setToken = useAuthToken((s) => s.setToken);

  useEffect(() => {
    if (authStrategy.name === "clerk") {
      authStrategy
        .loadComponents()
        .then((components) => {
          setClerkComponents(components);
          setIsLoading(false);
        })
        .catch((error) => {
          authLogger.error("Auth components failed to load", error);
          setIsLoading(false);
        });
    } else {
      setIsLoading(false);
    }
  }, [authStrategy]);

  useEffect(() => {
    // Set token to null when auth is disabled
    if (authStrategy.name !== "clerk") {
      setToken(null);
    }
  }, [authStrategy, setToken]);

  // While loading components, show children without auth wrapper
  if (isLoading) {
    return <>{children}</>;
  }

  // If not using Clerk or components failed to load, render fallback
  if (authStrategy.name !== "clerk" || !clerkComponents) {
    return authStrategy.renderFallback(children);
  }

  const { ClerkProvider, SignedIn, SignedOut, SignInButton, SignUpButton } = clerkComponents;

  // Render with Clerk functionality
  return (
    <ClerkProvider
      publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY!}
      signInFallbackRedirectUrl="/"
      afterSignOutUrl="/"
      signInUrl="/sign-in"
      signUpUrl="/sign-up"
    >
      <TokenSyncWrapper clerkComponents={clerkComponents}>
        <SignedOut>
          <div className="flex flex-col w-full h-screen bg-gray-50 justify-center items-center px-4">
            <div className="bg-white rounded-[2px] border border-gray-200 p-6 max-w-md w-full text-center shadow-sm">
              <div className="flex items-center justify-center gap-3 mb-6">
                <Image src="/sidebar-logo.png" alt="AnotherAI Logo" width={40} height={40} className="w-10 h-10" />
                <h1 className="text-2xl font-semibold text-gray-900">AnotherAI</h1>
              </div>
              <div className="mb-6">
                <p className="text-sm text-gray-600">Please sign in to continue</p>
              </div>
              <div className="space-y-2">
                <SignInButton mode="modal">
                  <button className="w-full bg-blue-600 text-white hover:bg-blue-700 cursor-pointer px-6 py-2 rounded-[2px] font-medium transition-colors duration-200">
                    Sign In
                  </button>
                </SignInButton>
                <div>
                  <span className="text-gray-600 text-sm">{`Don't have an account? `}</span>
                  <SignUpButton mode="modal">
                    <button className="text-gray-900 hover:text-gray-700 text-sm font-medium transition-colors duration-200 cursor-pointer">
                      Sign Up
                    </button>
                  </SignUpButton>
                </div>
              </div>
            </div>
          </div>
        </SignedOut>
        <SignedIn>{children}</SignedIn>
      </TokenSyncWrapper>
    </ClerkProvider>
  );
}

// Separate component for token sync to properly use hooks
function TokenSyncWrapper({ clerkComponents, children }: { clerkComponents: ClerkComponents; children: ReactNode }) {
  const { isLoaded, isSignedIn, getToken } = clerkComponents.useAuth();
  const setToken = useAuthToken((s) => s.setToken);

  useEffect(() => {
    if (!isLoaded) return;

    let stop = false;
    let intervalId: NodeJS.Timeout | null = null;
    let isSyncing = false;

    const syncWithRetry = async (maxRetries = 3, baseDelay = 1000) => {
      if (isSyncing || stop) return null;

      isSyncing = true;
      let syncedToken: string | null = null;

      try {
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
          if (stop) break;

          try {
            // Always try to get token - Clerk might have valid session even if isSignedIn is unclear
            const jwt = await getToken();
            syncedToken = jwt;
            if (!stop) {
              setToken(jwt ?? null);
            }
            authLogger.debug("Token sync successful", { hasToken: !!jwt });
            break; // Success, exit retry loop
          } catch (error) {
            const isLastAttempt = attempt === maxRetries;
            if (isLastAttempt) {
              authLogger.warn(`Token sync failed after ${maxRetries} attempts`, error);
              // Don't clear token on final failure, keep existing state
            } else {
              authLogger.debug(`Token sync attempt ${attempt} failed, retrying...`);
              // Exponential backoff: 1s, 2s, 4s
              const delay = baseDelay * Math.pow(2, attempt - 1);
              await new Promise((resolve) => setTimeout(resolve, delay));
            }
          }
        }
      } finally {
        isSyncing = false;
      }

      return syncedToken;
    };

    const scheduleNextRefresh = (token: string | null) => {
      if (stop) return;

      const refreshInterval = calculateRefreshInterval(token);

      intervalId = setTimeout(async () => {
        const newToken = await syncWithRetry();
        scheduleNextRefresh(newToken); // Schedule next refresh based on new token
      }, refreshInterval);
    };

    // Single consolidated token sync effect
    const handleTokenSync = async () => {
      try {
        // Clear any signed-out state immediately
        if (isSignedIn === false) {
          setToken(null);
          return null;
        }

        // Perform initial sync with retry
        const token = await syncWithRetry();

        // Schedule periodic refresh based on token
        scheduleNextRefresh(token);

        return token;
      } catch (error) {
        authLogger.error("Token sync initialization failed", error);
        return null;
      }
    };

    handleTokenSync();

    return () => {
      stop = true;
      if (intervalId) {
        clearTimeout(intervalId);
      }
    };
  }, [isLoaded, isSignedIn, getToken, setToken]);

  return <>{children}</>;
}
