"use client";

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(amount);
}

interface CreditBalanceSectionProps {
  balance: number;
}

export function CreditBalanceSection({ balance }: CreditBalanceSectionProps) {
  return (
    <div className="flex flex-col px-4 py-3 w-full">
      <div className="text-[13px] font-medium text-gray-900">Credits Balance</div>
      <div className="text-[15px] font-semibold text-gray-900">{formatCurrency(balance)}</div>
    </div>
  );
}
