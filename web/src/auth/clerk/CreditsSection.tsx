"use client";

import { cx } from "class-variance-authority";
import { AlertTriangle } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { CircularProgress } from "@/components/CircularProgress";
import { HoverPopover } from "@/components/HoverPopover";
import { PaymentModal } from "@/components/payment-modal/PaymentModal";
import { useOrFetchOrganizationSettings, useOrFetchPaymentMethod } from "@/store/mocked_payments";

interface CreditsSectionProps {
  className?: string;
}

function formatCurrency(amount?: number): string {
  if (amount === undefined || amount === null) return "$0.00";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(amount);
}

export function CreditsSection({ className }: CreditsSectionProps) {
  const { organizationSettings, isLoading } = useOrFetchOrganizationSettings(30000); // Refresh every 30s
  const { paymentMethod, isInitialized: isPaymentMethodInitialized } = useOrFetchPaymentMethod(30000);
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);

  const handleClick = useCallback(() => {
    setIsPaymentModalOpen(true);
  }, []);

  const currentCredits = organizationSettings?.current_credits_usd;
  const addedCredits = organizationSettings?.added_credits_usd;

  // Calculate progress percentage
  const progress = addedCredits === 0 || !currentCredits || !addedCredits ? 0 : (currentCredits / addedCredits) * 100;

  // Show warning when credits are low (≤ $5)
  const lowCreditsMode = !!currentCredits && currentCredits <= 5;

  // Payment method status
  const isPaymentMethodAvailable = !!paymentMethod?.payment_method_id;
  const automaticPaymentsEnabled = organizationSettings?.automatic_payment_enabled;
  const paymentFailure = organizationSettings?.payment_failure;

  // Tooltip text logic similar to WorkflowAI
  const tooltipText = useMemo(() => {
    if (!isPaymentMethodInitialized) {
      return "Loading payment information...";
    }

    if (!isPaymentMethodAvailable) {
      return "Payment method missing.\n\nTap the Credits section to add one\nand so you can continue using\nAnotherAI once your free credits\nare used.";
    }

    if (paymentFailure) {
      return `Auto Recharge failed:\n${paymentFailure.failure_reason}\n\nYou may run out of credits soon.\n\nTap the Credits section to update\nyour payment method.`;
    }

    if (automaticPaymentsEnabled) {
      return "Auto recharge is ON.\n\nTap to view and manage billing details";
    }

    return "Auto recharge is OFF.\n\nTap to view and manage billing details";
  }, [isPaymentMethodInitialized, isPaymentMethodAvailable, paymentFailure, automaticPaymentsEnabled]);

  if (isLoading && !organizationSettings) {
    return (
      <div
        className={cx(
          "flex gap-3 pl-5 pr-4 py-2 justify-between items-center border-t border-gray-200",
          "animate-pulse",
          className
        )}
      >
        <div className="flex flex-col space-y-1">
          <div className="w-12 h-3 bg-gray-200 rounded"></div>
          <div className="w-16 h-2 bg-gray-200 rounded"></div>
        </div>
        <div className="w-6 h-6 bg-gray-200 rounded-full"></div>
      </div>
    );
  }

  return (
    <>
      <HoverPopover
        content={<div className="text-xs text-white whitespace-pre-line max-w-60 p-1">{tooltipText}</div>}
        position="top"
        delay={0}
        popoverClassName="bg-gray-800 text-white rounded-[4px]"
      >
        <div
          className={cx(
            "flex gap-3 pl-5 pr-4 py-2 justify-between items-center border-t border-gray-200 w-full",
            "cursor-pointer transition-colors duration-200 hover:bg-gray-100",
            className
          )}
          onClick={handleClick}
        >
          <div className="flex flex-col">
            <div className="text-xs font-medium text-gray-800">{formatCurrency(currentCredits)}</div>
            <div className="text-xs font-normal text-gray-500">Credits Left</div>
          </div>

          <div className="relative flex w-6 h-6 items-center">
            <CircularProgress value={progress} warning={lowCreditsMode} size={24} />
            {lowCreditsMode && (
              <div className="absolute inset-0 flex items-center justify-center text-red-500">
                <AlertTriangle className="w-3 h-3" />
              </div>
            )}
          </div>
        </div>
      </HoverPopover>

      <PaymentModal isOpen={isPaymentModalOpen} onClose={() => setIsPaymentModalOpen(false)} />
    </>
  );
}