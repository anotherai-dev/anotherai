"use client";

// eslint-disable-next-line no-restricted-imports
import { AddressElement, CardElement, useElements, useStripe } from "@stripe/react-stripe-js";
import { useCallback, useState } from "react";
import { BottomButtonBar } from "../BottomButtonBar";
import { useStripePayments } from "../hooks/useStripePayments";

interface AddPaymentMethodContentProps {
  onClose: () => void;
}

export function AddPaymentMethodContent({ onClose }: AddPaymentMethodContentProps) {
  const [isLoading, setIsLoading] = useState(false);

  const stripe = useStripe();
  const elements = useElements();

  const { createPaymentMethod } = useStripePayments();

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!stripe || !elements) return;

      setIsLoading(true);

      try {
        await createPaymentMethod(elements);
        onClose();
      } catch (error) {
        console.error("Failed to add payment method:", error);
      } finally {
        setIsLoading(false);
      }
    },
    [createPaymentMethod, elements, onClose, stripe]
  );

  return (
    <div className="flex flex-col h-full w-full overflow-hidden bg-gray-50">
      <div className="text-[16px] font-semibold text-gray-900 px-4 py-3 border-b border-gray-200 border-dashed">
        Add Payment Method
      </div>

      <form onSubmit={handleSubmit}>
        <div className="flex flex-col px-4 py-4">
          <div className="text-gray-700 font-normal text-[13px]">Add your card details below</div>
          <div className="text-gray-500 font-normal text-xs">
            This card will be saved to your account and can be removed at any time
          </div>
        </div>

        <div className="flex flex-col px-4 pb-4 pt-2 gap-2">
          <div className="text-gray-900 font-medium text-[13px]">Card Information</div>
          <CardElement className="py-3 px-2 border border-gray-200 rounded-[4px] bg-white text-gray-900 text-[13px]" />
        </div>

        <div className="flex flex-col px-4 pb-4 pt-2 gap-2">
          <div className="text-gray-900 font-medium text-[13px]">Billing Address</div>
          <AddressElement options={{ mode: "billing" }} className="text-[13px]" />
        </div>

        <BottomButtonBar
          type="submit"
          actionText={isLoading ? "Adding..." : "Add Payment Method"}
          onCancel={onClose}
          onAction={handleSubmit}
          isActionDisabled={!stripe || !elements || isLoading}
        />
      </form>
    </div>
  );
}
