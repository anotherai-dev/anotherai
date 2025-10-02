"use client";

// eslint-disable-next-line no-restricted-imports
import { Elements } from "@stripe/react-stripe-js";
// eslint-disable-next-line no-restricted-imports
import { loadStripe } from "@stripe/stripe-js";
import { PaymentModalWrapper } from "./PaymentModalWrapper";

const STRIPE_PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;

const stripePromise = STRIPE_PUBLISHABLE_KEY ? loadStripe(STRIPE_PUBLISHABLE_KEY) : Promise.resolve(null);

export function StripeProvider({ onClose }: { onClose: () => void }) {
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
      <div className="bg-gray-50 rounded-[2px] border border-gray-200 shadow-xl max-w-md w-full mx-4 overflow-hidden">
        <PaymentModalWrapper onClose={onClose} />
      </div>
    </Elements>
  );
}
