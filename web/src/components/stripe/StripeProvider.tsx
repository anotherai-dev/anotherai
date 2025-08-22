"use client";

import { Elements } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";
import { ReactNode } from "react";
import { STRIPE_PUBLISHABLE_KEY } from "@/lib/constants";

const stripePromise = STRIPE_PUBLISHABLE_KEY ? loadStripe(STRIPE_PUBLISHABLE_KEY) : Promise.resolve(null);

export function StripeProvider({ children }: { children: ReactNode }) {
  return (
    <Elements
      stripe={stripePromise}
      options={{
        appearance: {
          disableAnimations: true,
          theme: "stripe",
          variables: {
            fontFamily: "system-ui, sans-serif",
            borderRadius: "4px",
            colorBackground: "white",
            fontSizeSm: "13px",
            focusBoxShadow: "0",
            focusOutline: "0",
            colorPrimary: "black",
            colorText: "#111827",
          },
          labels: "floating",
        },
      }}
    >
      {children}
    </Elements>
  );
}
