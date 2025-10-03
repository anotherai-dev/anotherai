"use client";

import { useCallback, useState } from "react";
import { useBillingStore, useOrFetchOrganizationSettings, useOrFetchPaymentMethod } from "@/store/billing";
import { useStripePayments } from "../hooks/useStripePayments";
import { PaymentModalContent } from "./PaymentModalContent";

interface PaymentModalWrapperProps {
  onClose: () => void;
}

export function PaymentModalWrapper({ onClose }: PaymentModalWrapperProps) {
  const { organizationSettings } = useOrFetchOrganizationSettings();
  const { paymentMethod } = useOrFetchPaymentMethod();
  const deletePaymentMethod = useBillingStore((state) => state.deletePaymentMethod);

  const { addCredits } = useStripePayments();

  const [showAddPaymentMethod, setShowAddPaymentMethod] = useState(false);
  const [showEnableAutoRecharge, setShowEnableAutoRecharge] = useState(false);
  const [amountToAdd, setAmountToAdd] = useState<number | undefined>(undefined);
  const [isProcessingPayment, setIsProcessingPayment] = useState(false);

  const isAddCreditsButtonActive =
    !!amountToAdd && !!paymentMethod?.payment_method_id && amountToAdd >= 5 && amountToAdd <= 5000;

  const reset = useCallback(() => {
    setShowAddPaymentMethod(false);
    setShowEnableAutoRecharge(false);
    setAmountToAdd(undefined);
  }, []);

  const handleAddCredits = useCallback(async () => {
    if (!amountToAdd || isProcessingPayment) {
      return;
    }

    setIsProcessingPayment(true);
    try {
      const success = await addCredits(amountToAdd);
      if (success) {
        reset();
        onClose();
      }
    } finally {
      setIsProcessingPayment(false);
    }
  }, [amountToAdd, isProcessingPayment, addCredits, reset, onClose]);

  const handleDeletePaymentMethod = useCallback(async () => {
    try {
      await deletePaymentMethod();
      console.log("Successfully deleted payment method");
      reset();
    } catch (error) {
      console.error("Failed to delete payment method:", error);
      throw error;
    }
  }, [deletePaymentMethod, reset]);

  const handleUpdatePaymentMethod = useCallback(async () => {
    console.log("Updating payment method");
    setShowAddPaymentMethod(true);
  }, []);

  return (
    <PaymentModalContent
      paymentMethod={paymentMethod}
      organizationSettings={organizationSettings}
      showAddPaymentMethod={showAddPaymentMethod}
      setShowAddPaymentMethod={setShowAddPaymentMethod}
      showEnableAutoRecharge={showEnableAutoRecharge}
      setShowEnableAutoRecharge={setShowEnableAutoRecharge}
      amountToAdd={amountToAdd}
      setAmountToAdd={setAmountToAdd}
      isAddCreditsButtonActive={isAddCreditsButtonActive}
      isProcessingPayment={isProcessingPayment}
      onAddCredits={handleAddCredits}
      onDeletePaymentMethod={handleDeletePaymentMethod}
      onUpdatePaymentMethod={handleUpdatePaymentMethod}
      onClose={onClose}
    />
  );
}
