"use client";

import { AuthComponentProps } from "../base";

export function SignedIn({ children }: AuthComponentProps) {
  // Right now we are always signed in
  return children;
}

export function SignedOut({}: AuthComponentProps) {
  // Right now we are always signed in
  return null;
}

export function SignInButton({}: AuthComponentProps) {
  return null;
}

export function SignUpButton({}: AuthComponentProps) {
  return null;
}

export function UserButton({}: { className?: string }) {
  return null;
}

export function ApiKeysButton({}: { onClick: () => void; className?: string }) {
  return null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return children;
}

export function SignIn({}: { redirect?: string }) {
  return null;
}

export function SignUp({}: { redirect?: string }) {
  return null;
}
