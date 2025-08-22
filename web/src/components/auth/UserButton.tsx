"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { isClerkEnabled } from "@/lib/utils";

interface ClerkUserComponents {
  UserButton: React.ComponentType<{ afterSignOutUrl?: string }>;
  useUser: () => {
    isSignedIn: boolean | undefined;
    user?: {
      firstName?: string | null;
      lastName?: string | null;
      emailAddresses?: Array<{ emailAddress: string }>;
    } | null;
  };
}

interface UserButtonWithClerkProps {
  clerkComponents: ClerkUserComponents;
  className?: string;
}

const UserButtonWithClerk = React.memo<UserButtonWithClerkProps>(function UserButtonWithClerk(props) {
  const { clerkComponents, className } = props;
  const { isSignedIn, user } = clerkComponents.useUser();
  const userButtonRef = useRef<HTMLDivElement>(null);
  const { UserButton: ClerkUserButton } = clerkComponents;

  // Extract user info
  const firstName = user?.firstName || "";
  const lastName = user?.lastName || "";
  const email = user?.emailAddresses?.[0]?.emailAddress || "";
  const fullName = [firstName, lastName].filter(Boolean).join(" ");

  // Handle sign-out detection and page reload
  useEffect(() => {
    if (isSignedIn === false) {
      window.location.reload();
    }
  }, [isSignedIn]);

  // Make the entire container clickable by triggering the Clerk button
  const handleContainerClick = useCallback(() => {
    const clerkButton = userButtonRef.current?.querySelector("button");
    clerkButton?.click();
  }, []);

  return (
    <div className={cn("w-full", className)}>
      <div
        ref={userButtonRef}
        onClick={handleContainerClick}
        className="flex gap-3 px-5 py-2.5 justify-between items-center hover:bg-gray-100 rounded-[4px] cursor-pointer transition-colors duration-200"
      >
        <ClerkUserButton afterSignOutUrl="/" />

        <div className="flex-1 min-w-0">
          {fullName && <div className="text-[13px] font-medium text-gray-900 truncate">{fullName}</div>}
          {email && <div className="text-xs text-gray-500 truncate">{email}</div>}
        </div>
      </div>
    </div>
  );
});

export const UserButton = React.memo<{ className?: string }>(function UserButton({ className } = {}) {
  const [clerkComponents, setClerkComponents] = useState<ClerkUserComponents | null>(null);
  const [loading, setLoading] = useState(isClerkEnabled());

  useEffect(() => {
    if (isClerkEnabled()) {
      import("@clerk/nextjs")
        .then((clerk) => {
          setClerkComponents({
            UserButton: clerk.UserButton,
            useUser: clerk.useUser,
          });
          setLoading(false);
        })
        .catch(() => {
          console.log("Clerk package not available");
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  // Show nothing while loading to prevent layout shifts
  if (loading) {
    return (
      <div className={cn("w-full", className)}>
        <div className="flex gap-1 mx-2 px-3 py-3 pt-4 justify-between items-center rounded-[4px]">
          <div className="w-8 h-8 bg-gray-200 rounded-full animate-pulse" />
        </div>
      </div>
    );
  }

  if (!isClerkEnabled() || !clerkComponents) {
    return null;
  }

  return <UserButtonWithClerk clerkComponents={clerkComponents} className={className} />;
});
