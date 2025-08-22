"use client";

import { Modal } from "@/components/Modal";
import { StripeWrapper } from "@/components/stripe/StripeWrapper";
import { PaymentModalWrapper } from "./PaymentModalWrapper";

interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PaymentModal({ isOpen, onClose }: PaymentModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <StripeWrapper>
        <div className="bg-gray-50 rounded-[2px] border border-gray-200 shadow-xl max-w-md w-full mx-4 overflow-hidden">
          <PaymentModalWrapper onClose={onClose} />
        </div>
      </StripeWrapper>
    </Modal>
  );
}
