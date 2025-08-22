"use client";

import { CreditCard, MoreVertical, Trash2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { PaymentMethodResponse } from "@/types/models";
import { DeletePaymentMethodModal } from "./DeletePaymentMethodModal";

interface PaymentMethodSectionProps {
  paymentMethod: PaymentMethodResponse | null;
  onAddPaymentMethod: () => void;
  onDeletePaymentMethod: () => Promise<void>;
}

export function PaymentMethodSection({
  paymentMethod,
  onAddPaymentMethod,
  onDeletePaymentMethod,
}: PaymentMethodSectionProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
      }
    }

    document.addEventListener("mouseup", handleClickOutside);
    return () => {
      document.removeEventListener("mouseup", handleClickOutside);
    };
  }, []);

  const toggleMenu = (event: React.MouseEvent) => {
    event.stopPropagation();
    setShowMenu(!showMenu);
  };

  const onShowDeleteConfirmation = useCallback((event: React.MouseEvent) => {
    event.stopPropagation();
    setShowMenu(false);
    setShowDeleteConfirmation(true);
  }, []);

  const onConfirm = useCallback(async () => {
    setIsDeleting(true);
    try {
      await onDeletePaymentMethod();
      setShowDeleteConfirmation(false);
    } catch (error) {
      // Handle error if needed
      console.error("Failed to delete payment method:", error);
    } finally {
      setIsDeleting(false);
    }
  }, [onDeletePaymentMethod]);

  return (
    <div className="flex flex-col gap-1 px-4 pt-1 pb-2">
      <div className="text-[13px] font-medium text-gray-900">Payment Method</div>
      {paymentMethod?.payment_method_id ? (
        <div className="flex flex-row gap-4 py-3 px-4 border border-gray-200 rounded-[4px] items-center relative">
          <div className="flex rounded-full bg-gray-100 border border-gray-200 w-10 h-10 items-center justify-center">
            <CreditCard className="w-5 h-5 text-gray-900" />
          </div>
          <div className="flex flex-col gap-0.5 h-fit flex-grow">
            <div className="text-[13px] font-semibold text-gray-700">••••{paymentMethod.last4}</div>
            <div className="text-xs font-normal text-gray-500">
              Expires {paymentMethod.exp_month}/{paymentMethod.exp_year}
            </div>
          </div>
          <div className="relative" ref={menuRef}>
            <button
              className="w-7 h-7 rounded-[4px] border border-gray-200 hover:bg-gray-100 flex items-center justify-center cursor-pointer"
              onClick={toggleMenu}
            >
              <MoreVertical className="w-4 h-4 text-gray-800" />
            </button>
            {showMenu && (
              <div className="absolute right-0 top-full mt-1 z-10 bg-white border border-gray-200 rounded-[4px] shadow-lg">
                <button
                  className="flex items-center gap-2 px-2.5 py-1.5 text-[13px] text-red-700 hover:bg-red-50 w-full text-left rounded-[4px] cursor-pointer"
                  onClick={onShowDeleteConfirmation}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Delete
                </button>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div>
          <button
            className="px-4 py-2 bg-indigo-600 text-white text-[13px] font-medium rounded-[2px] hover:bg-indigo-700 transition-colors cursor-pointer"
            onClick={onAddPaymentMethod}
          >
            Add Payment Method
          </button>
        </div>
      )}

      <DeletePaymentMethodModal
        isOpen={showDeleteConfirmation}
        onClose={() => setShowDeleteConfirmation(false)}
        onConfirm={onConfirm}
        paymentMethod={paymentMethod}
        isDeleting={isDeleting}
      />
    </div>
  );
}
