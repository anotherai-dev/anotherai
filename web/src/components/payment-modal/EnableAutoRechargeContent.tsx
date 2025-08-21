"use client";

import { OrganizationSettings } from "@/types/models";

interface EnableAutoRechargeContentProps {
  organizationSettings: OrganizationSettings | null;
  onClose: () => void;
}

export function EnableAutoRechargeContent({ organizationSettings, onClose }: EnableAutoRechargeContentProps) {
  return (
    <div className="flex flex-col h-full w-full">
      <div className="text-[15px] font-semibold text-gray-900 mb-4 border-b border-gray-200 border-dashed px-4 py-3">
        Enable Auto-Recharge
      </div>

      <div className="flex-1 px-4">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Trigger threshold (recharge when balance reaches)
            </label>
            <input
              type="number"
              defaultValue={organizationSettings?.automatic_payment_threshold ?? 10}
              className="w-full px-3 py-2 border border-gray-200 rounded-[4px] text-[13px] focus:outline-none focus:ring-1 focus:ring-gray-900"
              placeholder="10"
            />
          </div>

          <div>
            <label className="block text-[13px] font-medium text-gray-700 mb-1">
              Target balance (recharge to this amount)
            </label>
            <input
              type="number"
              defaultValue={organizationSettings?.automatic_payment_balance_to_maintain ?? 50}
              className="w-full px-3 py-2 border border-gray-200 rounded-[4px] text-[13px] focus:outline-none focus:ring-1 focus:ring-gray-900"
              placeholder="50"
            />
          </div>

          <div className="text-[12px] text-gray-500 pb-4">
            Auto-recharge will automatically add credits when your balance falls below the trigger threshold, bringing
            it back up to your target balance.
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
          className="px-4 py-2 bg-indigo-600 text-white text-[13px] font-semibold rounded-[2px] hover:bg-indigo-700 transition-colors cursor-pointer"
          onClick={() => {
            // TODO: Implement save logic
            console.log("Saving auto-recharge settings");
            onClose();
          }}
        >
          Save Settings
        </button>
      </div>
    </div>
  );
}
