// eslint-disable-next-line no-restricted-imports
import { useStripe } from "@stripe/react-stripe-js";
// eslint-disable-next-line no-restricted-imports
import { StripeElements } from "@stripe/stripe-js";
import { useCallback } from "react";
import { useBillingStore } from "@/store/billing";

const STRIPE_PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;

function errorMessage(error: unknown, defaultPrefix?: string): string {
  if (error && typeof error === "object" && "message" in error) {
    return error.message as string;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return defaultPrefix ? `${defaultPrefix}. Error: ${String(error)}` : `Error: ${String(error)}`;
}

export function useStripePayments() {
  const stripe = useStripe();

  const { createPaymentIntent, addPaymentMethod, fetchOrganizationSettings } = useBillingStore();

  const handlePaymentStatus = useCallback(
    async (clientSecret: string, amount: number) => {
      if (!stripe) return;

      const { error, paymentIntent } = await stripe.retrievePaymentIntent(clientSecret);

      if (error) throw error;

      switch (paymentIntent.status) {
        case "succeeded":
          break;

        case "requires_action":
        case "requires_confirmation":
          const result = await stripe.confirmPayment({
            clientSecret,
            redirect: "if_required",
          });

          if (result.error) {
            throw result.error;
          }

          await handlePaymentStatus(clientSecret, amount);
          break;

        case "requires_payment_method":
          throw new Error("Payment failed. Error: Your payment method was declined.");

        default:
          throw new Error(`Payment failed. Error: [${paymentIntent.status}]`);
      }
    },
    [stripe]
  );

  const addCredits = useCallback(
    async (amountToAdd: number) => {
      if (amountToAdd <= 0) {
        return false;
      }

      try {
        const result = await createPaymentIntent(amountToAdd);
        if (!result) throw new Error("Failed to create payment intent");

        // If Stripe is available, use it for payment confirmation
        if (stripe) {
          await handlePaymentStatus(result.client_secret, amountToAdd);
        }

        await fetchOrganizationSettings();
        console.log(`$${amountToAdd} in Credits Added Successfully`);
        return true;
      } catch (error) {
        console.error(errorMessage(error, "Payment failed"));
        return false;
      }
    },
    [createPaymentIntent, fetchOrganizationSettings, handlePaymentStatus, stripe]
  );

  const createPaymentMethod = useCallback(
    async (elements: StripeElements | undefined) => {
      // If Stripe is not available, use mock payment method creation
      if (!stripe || !elements) {
        if (!STRIPE_PUBLISHABLE_KEY) {
          // Mock payment method creation when Stripe is not configured
          const mockPaymentMethodId = `pm_mock_${Date.now()}`;
          await addPaymentMethod(mockPaymentMethodId);
          console.log("Payment Method Successfully Added (Mock)");
          return;
        }
        return;
      }

      try {
        const { paymentMethod, error } = await stripe.createPaymentMethod({
          elements,
          params: {
            type: "card",
          },
        });

        if (error) throw error;
        if (!paymentMethod) throw new Error("No payment method created");

        await addPaymentMethod(paymentMethod.id);
        console.log("Payment Method Successfully Added");
      } catch (error) {
        console.error(errorMessage(error));
        throw error;
      }
    },
    [addPaymentMethod, stripe]
  );

  return { addCredits, createPaymentMethod };
}
