"use client";

interface PaymentsFailedInfoLabelProps {
  className?: string;
  onUpdatePaymentMethod: () => void;
}

export function PaymentsFailedInfoLabel({ className, onUpdatePaymentMethod }: PaymentsFailedInfoLabelProps) {
  return (
    <div className={`bg-red-50 border-l-4 border-red-400 p-3 ${className}`}>
      <div className="text-[13px] text-red-700 mb-2">
        Your last payment failed. Update your payment method to continue using auto-recharge.
      </div>
      <button
        className="px-3 py-1 bg-red-600 text-white text-xs font-medium rounded hover:bg-red-700 transition-colors cursor-pointer"
        onClick={onUpdatePaymentMethod}
      >
        Update Payment Method
      </button>
    </div>
  );
}
