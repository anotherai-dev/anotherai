"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Edit, MoreVertical, Trash2 } from "lucide-react";
import { useCallback, useState } from "react";
import { useViews } from "@/store/views";
import PopoverMenu from "../DropdownMenu";
import { Modal } from "../Modal";

interface FolderMenuButtonProps {
  folderId: string;
  folderName?: string;
  onRename?: () => void;
  onMenuOpenChange?: (isOpen: boolean) => void;
}

export default function FolderMenuButton({
  folderId,
  folderName,
  onRename,
  onMenuOpenChange,
}: FolderMenuButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const { deleteViewFolder } = useViews();

  const handleOpenChange = useCallback(
    (open: boolean) => {
      setIsOpen(open);
      onMenuOpenChange?.(open);
    },
    [onMenuOpenChange]
  );

  const handleRenameClick = useCallback(() => {
    onRename?.();
  }, [onRename]);

  const handleRemoveClick = useCallback(() => {
    setShowConfirmModal(true);
  }, []);

  const handleConfirmRemove = useCallback(async () => {
    setShowConfirmModal(false);

    try {
      await deleteViewFolder(folderId);
    } catch (error) {
      console.error("Failed to delete folder:", error);
    }
  }, [folderId, deleteViewFolder]);

  const handleCancelRemove = useCallback(() => {
    setShowConfirmModal(false);
  }, []);

  // Don't show menu for root folder (empty ID)
  if (folderId === "") {
    return null;
  }

  const trigger = (
    <button
      className={`p-1 rounded transition-colors focus:outline-none ${
        isOpen
          ? "opacity-100 bg-gray-200"
          : "opacity-0 group-hover/folder:opacity-100"
      } hover:bg-gray-200`}
      onClick={(e) => {
        e.stopPropagation();
      }}
    >
      <MoreVertical className="w-[14px] h-[14px]" />
    </button>
  );

  return (
    <>
      <PopoverMenu trigger={trigger} onOpenChange={handleOpenChange}>
        <DropdownMenu.Item
          className="w-full flex items-center gap-2 px-2 py-2 text-xs text-gray-700 hover:bg-gray-50 transition-colors cursor-pointer outline-none"
          onClick={handleRenameClick}
        >
          <Edit className="w-3 h-3" />
          Rename
        </DropdownMenu.Item>
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
            Remove Folder
          </h3>
          <div className="text-[13px] text-gray-600 mb-4 px-4 border-b border-gray-100 pb-4">
            <p>
              Are you sure you want to remove the folder{" "}
              <span className="font-semibold text-gray-900">
                {folderName || "Untitled"}
              </span>
              ?
            </p>
            <p className="mt-2">
              <strong>
                All views in this folder will be moved to the Default Folder.
              </strong>
            </p>
            <p className="text-red-600 mt-1">This action cannot be undone.</p>
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
