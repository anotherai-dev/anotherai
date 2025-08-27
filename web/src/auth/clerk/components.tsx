/* eslint-disable no-restricted-imports */
import { ClerkProvider } from "@clerk/nextjs";
import {
  SignIn as ClerkSignIn,
  SignInButton as ClerkSignInButton,
  SignUp as ClerkSignUp,
  SignUpButton as ClerkSignUpButton,
} from "@clerk/nextjs";
import type { AuthComponentProps } from "../base";

export { SignedIn, SignedOut } from "@clerk/nextjs";
export { UserButton } from "./UserButton";

export { ApiKeysButton } from "@/components/auth/ApiKeysButton";

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
