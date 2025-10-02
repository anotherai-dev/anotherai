"use client";

import { useCallback, useState } from "react";
import { useBillingStore } from "@/store/billing";
import { AutomaticPayment } from "@/types/models";

interface CurrencyInputProps {
  amount: number | undefined;
  setAmount: (amount: number | undefined) => void;
  placeholder?: string;
}

function CurrencyInput({ amount, setAmount, placeholder = "0.00" }: CurrencyInputProps) {
  const [isFocused, setIsFocused] = useState(false);

  const updateAmount = useCallback(
    (text: string) => {
      if (!text) {
        setAmount(undefined);
        return;
      }
      const parsedAmount = Number(text);
      setAmount(Number.isNaN(parsedAmount) ? undefined : parsedAmount);
    },
    [setAmount]
  );

  return (
    <div className="relative">
      <span
        className={`absolute left-3 top-1/2 -translate-y-1/2 text-[13px] font-normal ${
          isFocused || !!amount ? "text-gray-900" : "text-gray-400"
        }`}
      >
        $
      </span>
      <input
        type="number"
        value={amount ?? ""}
        onChange={(e) => updateAmount(e.target.value)}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        className="w-full pl-6 pr-3 py-2 border border-gray-200 rounded-[4px] text-[13px] font-normal text-gray-900 focus:outline-none focus:ring-1 focus:ring-gray-900 focus:border-transparent"
        placeholder={placeholder}
      />
    </div>
  );
}

interface EnableAutoRechargeContentProps {
  automaticPayment: AutomaticPayment | undefined | null;
  onClose: () => void;
}

export function EnableAutoRechargeContent({ automaticPayment, onClose }: EnableAutoRechargeContentProps) {
  const [triggerThreshold, setTriggerThreshold] = useState<number | undefined>(automaticPayment?.threshold ?? 10);
  const [targetBalance, setTargetBalance] = useState<number | undefined>(automaticPayment?.balance_to_maintain ?? 50);
  const [isEnabled, setIsEnabled] = useState<boolean>(automaticPayment?.opt_in ?? true);
  const [isSaving, setIsSaving] = useState(false);

  const { updateAutomaticPayments } = useBillingStore();

  const isValidConfiguration = () => {
    if (!triggerThreshold || !targetBalance) return false;
    return targetBalance > triggerThreshold;
  };

  const isSaveDisabled = !isValidConfiguration() || isSaving;

  const handleSave = async () => {
    if (isSaveDisabled) return;

    setIsSaving(true);
    try {
      await updateAutomaticPayments({
        opt_in: isEnabled,
        threshold: triggerThreshold,
        balance_to_maintain: targetBalance,
      });
      onClose();
    } catch (error) {
      console.error("Failed to save auto-recharge settings:", error);
      // TODO: Show error toast/notification
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex flex-col h-full w-full">
      <div className="text-[15px] font-semibold text-gray-900 mb-4 border-b border-gray-200 border-dashed px-4 py-3 cursor-pointer">
        Enable Auto-Recharge
      </div>

      <div className="flex-1 px-4">
        <div className="space-y-4">
          <div>
            <label className="flex items-center space-x-2 mb-4">
              <input
                type="checkbox"
                checked={isEnabled}
                onChange={(e) => setIsEnabled(e.target.checked)}
                className="w-4 h-4 text-indigo-600 bg-gray-100 border-gray-300 rounded focus:ring-indigo-500 focus:ring-2"
              />
              <span className="text-[13px] font-medium text-gray-700">
                Enable auto-recharge
              </span>
            </label>
          </div>

          <div className={`space-y-4 ${!isEnabled ? 'opacity-50' : ''}`}>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Trigger threshold (recharge when balance reaches)
              </label>
              <CurrencyInput 
                amount={triggerThreshold} 
                setAmount={setTriggerThreshold} 
                placeholder="10.00" 
              />
            </div>

            <div>
              <label className="block text-[13px] font-medium text-gray-700 mb-1">
                Target balance (recharge to this amount)
              </label>
              <CurrencyInput 
                amount={targetBalance} 
                setAmount={setTargetBalance} 
                placeholder="50.00" 
              />
              <div className="text-[12px] text-gray-500 mt-1">
                Enter an amount between $5 and $5000. Target balance must be higher than trigger threshold.
              </div>
              {isEnabled && triggerThreshold && targetBalance && targetBalance <= triggerThreshold && (
                <div className="text-[12px] text-red-600 mt-1">
                  Target balance must be higher than trigger threshold
                </div>
              )}
            </div>

            <div className="text-[12px] text-gray-500 pb-4">
              Auto-recharge will automatically add credits when your balance falls below the trigger threshold, bringing
              it back up to your target balance.
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-2 border-t border-gray-200 px-4 py-4">
        <button
          className="px-4 py-2 bg-gray-200 text-gray-700 text-[13px] font-semibold rounded-[2px] hover:bg-gray-300 transition-colors cursor-pointer"
          onClick={onClose}
        >
          Cancel
        </button>
        <button
          className="px-4 py-2 bg-indigo-600 text-white text-[13px] font-semibold rounded-[2px] hover:bg-indigo-700 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={handleSave}
          disabled={isSaveDisabled}
        >
          {isSaving ? "Saving..." : "Save Settings"}
        </button>
      </div>
    </div>
  );
}
