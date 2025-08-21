import { ReactNode } from "react";
import { STRIPE_PUBLISHABLE_KEY } from "@/lib/constants";
import { StripeProvider } from "./StripeProvider";

export function StripeWrapper({ children }: { children: ReactNode }) {
  // Always provide Stripe context, even if not configured
  return <StripeProvider>{children}</StripeProvider>;
}
