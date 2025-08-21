"use client";

import { useCallback, useState } from "react";

interface CurrencyInputProps {
  amount: number | undefined;
  setAmount: (amount: number | undefined) => void;
}

function CurrencyInput({ amount, setAmount }: CurrencyInputProps) {
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
        placeholder="0.00"
      />
    </div>
  );
}

interface AmountToAddSectionProps {
  amountToAdd: number | undefined;
  setAmountToAdd: (amount: number | undefined) => void;
}

export function AmountToAddSection({ amountToAdd, setAmountToAdd }: AmountToAddSectionProps) {
  return (
    <div className="flex flex-col px-4 py-2 gap-1">
      <div className="flex flex-col gap-1">
        <div className="text-gray-900 font-medium text-[13px]">Amount to Add</div>
        <CurrencyInput amount={amountToAdd} setAmount={setAmountToAdd} />
        <div className="text-gray-500 font-normal text-xs">Enter an amount between $5 and $4902</div>
      </div>
    </div>
  );
}
