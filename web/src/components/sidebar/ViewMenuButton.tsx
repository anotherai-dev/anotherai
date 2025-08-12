"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { MoreVertical, Trash2 } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import { useViews } from "@/store/views";
import PopoverMenu from "../DropdownMenu";
import { Modal } from "../Modal";

interface ViewMenuButtonProps {
  viewId: string;
  viewName?: string;
  isActive?: boolean;
  onRemove?: (viewId: string) => void;
}

export default function ViewMenuButton({
  viewId,
  viewName,
  isActive = false,
  onRemove,
}: ViewMenuButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const router = useRouter();
  const pathname = usePathname();
  const { deleteView } = useViews();

  const handleRemoveClick = useCallback(() => {
    setShowConfirmModal(true);
  }, []);

  const handleConfirmRemove = useCallback(async () => {
    setShowConfirmModal(false);

    if (onRemove) {
      onRemove(viewId);
    } else {
      // Check if we're currently viewing this view's page
      const isCurrentlyViewing = pathname === `/view/${viewId}`;

      await deleteView(viewId);

      // If we were viewing the deleted view, redirect to completions page
      if (isCurrentlyViewing) {
        router.push("/completions");
      }
    }
  }, [viewId, onRemove, deleteView, router, pathname]);

  const handleCancelRemove = useCallback(() => {
    setShowConfirmModal(false);
  }, []);

  const trigger = (
    <button
      className={`absolute top-2 right-2 p-1 rounded transition-colors focus:outline-none ${
        isOpen ? "opacity-100" : "opacity-0 group-hover:opacity-100"
      } ${isActive ? "hover:bg-blue-200" : "hover:bg-gray-200"}`}
      onClick={(e) => e.stopPropagation()}
    >
      <MoreVertical className="w-4 h-4" />
    </button>
  );

  return (
    <>
      <PopoverMenu trigger={trigger} onOpenChange={setIsOpen}>
        <DropdownMenu.Item
          className="w-full flex items-center gap-2 px-2 py-2 text-xs text-red-600 hover:bg-red-50 transition-colors cursor-pointer outline-none"
          onClick={handleRemoveClick}
        >
          <Trash2 className="w-3 h-3" />
          Remove
        </DropdownMenu.Item>
      </PopoverMenu>

      <Modal isOpen={showConfirmModal} onClose={handleCancelRemove}>
        <div className="bg-white rounded-[2px] border border-gray-200 shadow-lg py-4 max-w-md mx-auto">
          <h3 className="text-base font-bold text-gray-900 mb-4 border-b border-gray-200 border-dashed pb-4 px-4">
            Remove View
          </h3>
          <div className="text-[13px] text-gray-600 mb-4 px-4 border-b border-gray-100 pb-4">
            <p>
              Are you sure you want to remove the view{" "}
              <span className="font-semibold text-gray-900">
                {viewName || "Untitled"}
              </span>
              ?
            </p>
            <p>This action cannot be undone.</p>
          </div>
          <div className="flex justify-end gap-2 px-4">
            <button
              onClick={handleCancelRemove}
              className="bg-white border border-gray-200 text-gray-900 font-semibold hover:bg-gray-100 cursor-pointer px-2 py-1 rounded-[2px] shadow-sm shadow-black/5 text-[13px]"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirmRemove}
              className="bg-red-600 border border-red-600 text-white font-semibold hover:bg-red-700 cursor-pointer px-2 py-1 rounded-[2px] shadow-sm shadow-black/5 text-[13px]"
            >
              Remove
            </button>
          </div>
        </div>
      </Modal>
    </>
  );
}
