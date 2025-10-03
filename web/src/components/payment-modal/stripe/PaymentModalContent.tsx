"use client";

import { PaymentMethodResponse, Tenant } from "@/types/models";
import { AmountToAddSection } from "../AmountToAddSection";
import { AutomaticPaymentsSection } from "../AutomaticPaymentsSection";
import { BottomButtonBar } from "../BottomButtonBar";
import { CreditBalanceSection } from "../CreditBalanceSection";
import { EnableAutoRechargeContent } from "../EnableAutoRechargeContent";
import { InfoLabel } from "../InfoLabel";
import { PaymentMethodSection } from "../PaymentMethodSection";
import { AddPaymentMethodContent } from "./AddPaymentMethodContent";

interface PaymentModalContentProps {
  paymentMethod: PaymentMethodResponse | null;
  organizationSettings: Tenant | null;
  showAddPaymentMethod: boolean;
  setShowAddPaymentMethod: (show: boolean) => void;
  showEnableAutoRecharge: boolean;
  setShowEnableAutoRecharge: (show: boolean) => void;
  amountToAdd: number | undefined;
  setAmountToAdd: (amount: number | undefined) => void;
  isAddCreditsButtonActive: boolean;
  isProcessingPayment: boolean;
  onAddCredits: () => void;
  onDeletePaymentMethod: () => Promise<void>;
  onUpdatePaymentMethod: () => void;
  onClose: () => void;
}

export function PaymentModalContent({
  paymentMethod,
  organizationSettings,
  showAddPaymentMethod,
  setShowAddPaymentMethod,
  showEnableAutoRecharge,
  setShowEnableAutoRecharge,
  amountToAdd,
  setAmountToAdd,
  isAddCreditsButtonActive,
  isProcessingPayment,
  onAddCredits,
  onDeletePaymentMethod,
  onUpdatePaymentMethod,
  onClose,
}: PaymentModalContentProps) {
  const balance = organizationSettings?.current_credits_usd;
  const isPaymentMethodAvailable = !!paymentMethod?.payment_method_id;
  const automaticPaymentsFailure = organizationSettings?.payment_failure?.failure_reason;

  if (showAddPaymentMethod) {
    return <AddPaymentMethodContent onClose={() => setShowAddPaymentMethod(false)} />;
  }

  if (showEnableAutoRecharge) {
    return (
      <EnableAutoRechargeContent
        automaticPayment={organizationSettings?.automatic_payment}
        onClose={() => setShowEnableAutoRecharge(false)}
      />
    );
  }

  return (
    <div className="flex flex-col h-full w-full overflow-hidden bg-gray-50">
      <div className="text-[16px] font-semibold text-gray-900 px-4 py-3 border-b border-gray-200 border-dashed">
        Add to Credits Balance
      </div>

      {!isPaymentMethodAvailable && (
        <InfoLabel text="Set up a payment method to start adding credits to your account." />
      )}

      {balance !== undefined && <CreditBalanceSection balance={balance} />}

      <PaymentMethodSection
        paymentMethod={paymentMethod}
        onAddPaymentMethod={() => setShowAddPaymentMethod(true)}
        onDeletePaymentMethod={onDeletePaymentMethod}
      />

      <AmountToAddSection amountToAdd={amountToAdd} setAmountToAdd={setAmountToAdd} />

      <AutomaticPaymentsSection
        hasPaymentMethod={isPaymentMethodAvailable}
        automaticPaymentsFailure={automaticPaymentsFailure}
        automaticPayment={organizationSettings?.automatic_payment}
        onEnableAutoRecharge={() => setShowEnableAutoRecharge(true)}
        onUpdatePaymentMethod={onUpdatePaymentMethod}
      />

      <BottomButtonBar
        tooltipText={!isPaymentMethodAvailable ? "Add a Payment method before adding credits" : undefined}
        actionText={isProcessingPayment ? "Processing..." : "Add Credits"}
        isActionDisabled={!isAddCreditsButtonActive || isProcessingPayment}
        onCancel={onClose}
        onAction={onAddCredits}
      />
    </div>
  );
}
