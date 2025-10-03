"use client";

import { useCallback, useMemo, useState } from "react";
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
  const [isSaving, setIsSaving] = useState(false);
  const [isToggleEnabled, setIsToggleEnabled] = useState<boolean>(
    automaticPayment !== null && automaticPayment !== undefined
  );

  const isAutoRechargeEnabled = useMemo(
    () => automaticPayment !== null && automaticPayment !== undefined,
    [automaticPayment]
  );

  const { updateAutomaticPayments } = useBillingStore();

  const isTargetBalanceInvalid =
    targetBalance !== undefined && triggerThreshold !== undefined && targetBalance <= triggerThreshold;

  const handleSave = async () => {
    if (isSaving || isTargetBalanceInvalid) return;

    setIsSaving(true);
    try {
      // If auto-recharge is currently enabled, respect the toggle state
      // If auto-recharge is currently disabled, enable it by default
      const optIn = isAutoRechargeEnabled ? isToggleEnabled : true;
      await updateAutomaticPayments({
        opt_in: optIn,
        threshold: optIn ? triggerThreshold : undefined,
        balance_to_maintain: optIn ? targetBalance : undefined,
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
        {isAutoRechargeEnabled ? "Auto-Recharge Settings" : "Enable Auto-Recharge"}
      </div>

      <div className="flex-1 px-4">
        <div className="space-y-4">
          {isAutoRechargeEnabled && (
            <div
              className={`flex items-center gap-3 pb-3 px-4 -mx-4 ${isToggleEnabled ? "border-b border-gray-200" : ""}`}
            >
              <div className="flex items-center">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isToggleEnabled}
                    onChange={(e) => setIsToggleEnabled(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    className={`w-11 h-6 bg-gray-200 rounded-full peer transition-colors ${
                      isToggleEnabled ? "bg-gray-900" : "bg-gray-200"
                    }`}
                  >
                    <div
                      className={`absolute top-0.5 left-0.5 bg-white border border-gray-300 rounded-full h-5 w-5 transition-transform ${
                        isToggleEnabled ? "translate-x-5 border-gray-900" : ""
                      }`}
                    ></div>
                  </div>
                </label>
              </div>
              <div>
                <div className="text-[13px] text-gray-900 mb-1">
                  Yes, automatically recharge my card when my credit balance falls below a threshold.
                </div>
              </div>
            </div>
          )}

          {(!isAutoRechargeEnabled || isToggleEnabled) && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Trigger threshold (recharge when balance reaches)
                </label>
                <CurrencyInput amount={triggerThreshold} setAmount={setTriggerThreshold} placeholder="10.00" />
              </div>

              <div>
                <label className="block text-[13px] font-medium text-gray-700 mb-1">
                  Target balance (recharge to this amount)
                </label>
                <CurrencyInput amount={targetBalance} setAmount={setTargetBalance} placeholder="50.00" />
                <div className="text-[12px] text-gray-500 mt-1">Enter an amount between $5 and $5000</div>
              </div>

              <div className="text-[12px] text-gray-500 pb-4">
                Auto-recharge will automatically add credits when your balance falls below the trigger threshold,
                bringing it back up to your target balance.
              </div>
            </>
          )}
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
          disabled={isSaving || isTargetBalanceInvalid}
        >
          {isSaving ? "Saving..." : "Save Settings"}
        </button>
      </div>
    </div>
  );
}
