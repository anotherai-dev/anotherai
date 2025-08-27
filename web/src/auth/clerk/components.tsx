/* eslint-disable no-restricted-imports */
import { ClerkProvider, useUser } from "@clerk/nextjs";
import {
  SignIn as ClerkSignIn,
  SignInButton as ClerkSignInButton,
  SignUp as ClerkSignUp,
  SignUpButton as ClerkSignUpButton,
  UserButton as ClerkUserButton,
} from "@clerk/nextjs";
import { useCallback, useEffect, useRef } from "react";
import { cn } from "@/lib/cn";
import type { AuthComponentProps } from "../base";

export { SignedIn, SignedOut } from "@clerk/nextjs";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider signInFallbackRedirectUrl="/" afterSignOutUrl="/" signInUrl="/sign-in" signUpUrl="/sign-up">
      {children}
    </ClerkProvider>
  );
}

export function SignInButton(props: AuthComponentProps) {
  return <ClerkSignInButton mode="modal" {...props}></ClerkSignInButton>;
}

export function SignUpButton(props: AuthComponentProps) {
  return <ClerkSignUpButton mode="modal" {...props}></ClerkSignUpButton>;
}

export function SignIn({ redirect }: { redirect?: string }) {
  return <ClerkSignIn forceRedirectUrl={redirect} signUpForceRedirectUrl={redirect} />;
}

export function SignUp({ redirect }: { redirect?: string }) {
  return <ClerkSignUp forceRedirectUrl={redirect} signInForceRedirectUrl={redirect} />;
}

export function UserButton({ className }: { className?: string }) {
  const { isSignedIn, user } = useUser();
  const userButtonRef = useRef<HTMLDivElement>(null);

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
        className="flex gap-3 mx-2 px-3 py-2 mt-1.5 justify-between items-center hover:bg-gray-100 rounded-[4px] cursor-pointer transition-colors duration-200"
      >
        <ClerkUserButton />

        <div className="flex-1 min-w-0">
          {fullName && <div className="text-[13px] font-medium text-gray-900 truncate">{fullName}</div>}
          {email && <div className="text-xs text-gray-500 truncate">{email}</div>}
        </div>
      </div>
    </div>
  );
}
