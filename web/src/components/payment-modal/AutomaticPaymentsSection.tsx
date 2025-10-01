"use client";

import { CheckCircle, XCircle } from "lucide-react";
import { AutomaticPayment } from "@/types/models";
import { PaymentsFailedInfoLabel } from "./PaymentsFailedInfoLabel";

interface AutomaticPaymentsSectionProps {
  automaticPaymentsFailure: string | undefined;
  hasPaymentMethod: boolean;
  automaticPayment: AutomaticPayment | null | undefined;
  onEnableAutoRecharge: () => void;
  onUpdatePaymentMethod: () => void;
}

function EnabledAutomaticPaymentsSection({
  automaticPayment,
  onEnableAutoRecharge,
}: {
  automaticPayment: AutomaticPayment;
  onEnableAutoRecharge: () => void;
}) {
  return (
    <div className="flex flex-col">
      <div className="flex flex-row items-center gap-1">
        <CheckCircle className="text-green-500 w-4 h-4" />
        <div className="text-gray-700 font-normal text-[13px] pr-1">
          Auto recharge is <span className="font-semibold">on</span>.
        </div>
      </div>
      <div className="text-gray-500 font-normal text-xs pt-1">
        When your credit balance reaches ${automaticPayment.threshold ?? 10}, your payment method will be charged to
        bring the balance up to ${automaticPayment.balance_to_maintain ?? 50}.
      </div>
      <div className="pt-2">
        <button
          className="px-3 py-2 bg-gray-200 text-gray-700 text-[12px] font-semibold rounded-[2px] hover:bg-gray-300 transition-colors cursor-pointer"
          onClick={onEnableAutoRecharge}
        >
          Modify Auto-Recharge
        </button>
      </div>
    </div>
  );
}

export function AutomaticPaymentsSection({
  automaticPayment,
  onEnableAutoRecharge,
  automaticPaymentsFailure,
  hasPaymentMethod,
  onUpdatePaymentMethod,
}: AutomaticPaymentsSectionProps) {
  const isAutomaticPaymentsEnabled = !!automaticPayment;

  return (
    <div className="flex flex-col px-4 py-2 gap-1 mb-2">
      <div className="text-gray-900 font-medium text-[13px]">Automatic Payments</div>
      {automaticPaymentsFailure && (
        <PaymentsFailedInfoLabel
          className="py-3 flex w-full whitespace-pre-line"
          onUpdatePaymentMethod={onUpdatePaymentMethod}
        />
      )}
      {isAutomaticPaymentsEnabled && !automaticPaymentsFailure ? (
        <EnabledAutomaticPaymentsSection
          automaticPayment={automaticPayment}
          onEnableAutoRecharge={onEnableAutoRecharge}
        />
      ) : (
        <div className="flex flex-col">
          <div className="flex flex-row items-center gap-1">
            <XCircle className="text-gray-400 w-4 h-4" />
            <div className="text-gray-700 font-normal text-sm">
              Auto recharge is <span className="font-semibold">off</span>.
            </div>
          </div>
          <div className="text-gray-500 font-normal text-xs pt-1">
            {hasPaymentMethod
              ? "Enable automatic recharge to automatically keep your credit balance topped up."
              : "Set up a payment method to enable automatic recharge."}
          </div>

          <div className="pt-2">
            <button
              className={`px-3 py-2 text-[13px] font-medium rounded-[2px] transition-colors ${
                hasPaymentMethod
                  ? "bg-indigo-600 text-white hover:bg-indigo-700"
                  : "bg-gray-200 text-gray-400 cursor-not-allowed"
              }`}
              onClick={onEnableAutoRecharge}
              disabled={!hasPaymentMethod}
            >
              Enable Auto-Recharge
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
