"use client";

import dynamic from "next/dynamic";
import { Modal } from "@/components/Modal";

interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const StripeProvider = dynamic(() => import("./stripe/StripeProvider").then((mod) => mod.StripeProvider));

function NoopPaymentsProvider({}: { onClose: () => void }) {
  return <div className="flex flex-col items-center justify-center h-full">Payments are not configured</div>;
}

const PaymentsProvider = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY ? StripeProvider : NoopPaymentsProvider;

export function PaymentModal({ isOpen, onClose }: PaymentModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <PaymentsProvider onClose={onClose} />
    </Modal>
  );
}
