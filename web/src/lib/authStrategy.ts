"use client";

import React, { ReactNode } from "react";
import { isClerkEnabled } from "@/lib/utils";

export interface AuthStrategy {
  name: string;
  isEnabled: () => boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  loadComponents: () => Promise<any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  renderProvider: (_components: any, children: ReactNode) => ReactNode;
  renderFallback: (children: ReactNode) => ReactNode;
}

export class ClerkAuthStrategy implements AuthStrategy {
  name = "clerk";

  isEnabled(): boolean {
    return isClerkEnabled();
  }

  async loadComponents() {
    const clerk = await import("@clerk/nextjs");
    return {
      ClerkProvider: clerk.ClerkProvider,
      SignedIn: clerk.SignedIn,
      SignedOut: clerk.SignedOut,
      SignInButton: clerk.SignInButton,
      SignUpButton: clerk.SignUpButton,
      UserButton: clerk.UserButton,
      useAuth: clerk.useAuth,
      useUser: clerk.useUser,
    };
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars
  renderProvider(_components: any, _children: ReactNode): ReactNode {
    // This will be implemented by the component using the strategy
    throw new Error("renderProvider should be implemented by the component");
  }

  renderFallback(children: ReactNode): ReactNode {
    return React.createElement(React.Fragment, null, children);
  }
}

export class NoAuthStrategy implements AuthStrategy {
  name = "none";

  isEnabled(): boolean {
    return true; // Always available as fallback
  }

  async loadComponents() {
    return null;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  renderProvider(_components: any, children: ReactNode): ReactNode {
    return React.createElement(React.Fragment, null, children);
  }

  renderFallback(children: ReactNode): ReactNode {
    return React.createElement(React.Fragment, null, children);
  }
}

export function getAuthStrategy(): AuthStrategy {
  const strategies = [new ClerkAuthStrategy(), new NoAuthStrategy()];
  return strategies.find((strategy) => strategy.isEnabled()) || new NoAuthStrategy();
}
