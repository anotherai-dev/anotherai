/*
Type only file to make sure auth modules implement the correct types
*/
import type { NextMiddleware } from "next/server";

export interface AuthServer {
  middleware: NextMiddleware;
  getToken: () => Promise<string | null>;
}

export interface AuthComponentProps {
  children: React.ReactNode;
  className?: string;
}

export interface Components {
  SignedIn: React.ComponentType<AuthComponentProps>;
  SignedOut: React.ComponentType<AuthComponentProps>;
  SignInButton: React.ComponentType<AuthComponentProps>;
  SignUpButton: React.ComponentType<AuthComponentProps>;
  UserButton: React.ComponentType<{ className?: string }>;
  ApiKeysButton: React.ComponentType<{ onClick: () => void; className?: string }>;
  CreditsSection: React.ComponentType<{ className?: string }>;
  AuthProvider: React.ComponentType<AuthComponentProps>;
  SignIn: React.ComponentType<{ redirect?: string }>;
  SignUp: React.ComponentType<{ redirect?: string }>;
}
