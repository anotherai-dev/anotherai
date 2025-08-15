"use client";

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { useViews } from "@/store/views";

interface EditableFolderNameProps {
  folderId: string;
  name: string;
  className?: string;
}

export interface EditableFolderNameRef {
  startEditing: () => void;
}

const EditableFolderName = forwardRef<
  EditableFolderNameRef,
  EditableFolderNameProps
>(function EditableFolderName({ folderId, name, className = "" }, ref) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(name);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const focusTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const blurTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const { patchViewFolder } = useViews();

  const startEditing = useCallback(() => {
    // Don't allow editing the root folder (empty ID)
    if (folderId === "") {
      return;
    }
    setIsEditing(true);
  }, [folderId]);

  useImperativeHandle(
    ref,
    () => ({
      startEditing,
    }),
    [startEditing]
  );

  // Reset edit value when name changes from outside
  useEffect(() => {
    if (!isEditing) {
      setEditValue(name);
    }
  }, [name, isEditing]);

  // Focus input when entering edit mode
  useEffect(() => {
    if (isEditing && inputRef.current) {
      // Clear any existing timeout
      if (focusTimeoutRef.current) {
        clearTimeout(focusTimeoutRef.current);
      }

      // Small delay to ensure input is rendered
      focusTimeoutRef.current = setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
          inputRef.current.select();
        }
        focusTimeoutRef.current = null;
      }, 50);
    }

    return () => {
      // Clean up timeout on unmount or when isEditing changes
      if (focusTimeoutRef.current) {
        clearTimeout(focusTimeoutRef.current);
        focusTimeoutRef.current = null;
      }
    };
  }, [isEditing]);

  const handleDoubleClick = useCallback(() => {
    startEditing();
  }, [startEditing]);

  const handleSubmit = useCallback(async () => {
    if (isSubmitting || editValue.trim() === name.trim()) {
      setIsEditing(false);
      setEditValue(name);
      return;
    }

    const trimmedValue = editValue.trim();
    if (!trimmedValue) {
      setEditValue(name);
      setIsEditing(false);
      return;
    }

    setIsSubmitting(true);
    try {
      await patchViewFolder(folderId, { name: trimmedValue });
      setIsEditing(false);
    } catch (error) {
      console.error("Failed to update folder name:", error);
      // Reset to original name on error
      setEditValue(name);
      setIsEditing(false);
    } finally {
      setIsSubmitting(false);
    }
  }, [folderId, editValue, name, patchViewFolder, isSubmitting]);

  const handleCancel = useCallback(() => {
    setEditValue(name);
    setIsEditing(false);
  }, [name]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleSubmit();
      } else if (e.key === "Escape") {
        e.preventDefault();
        handleCancel();
      }
    },
    [handleSubmit, handleCancel]
  );

  const handleBlur = useCallback(() => {
    // Clear any existing blur timeout
    if (blurTimeoutRef.current) {
      clearTimeout(blurTimeoutRef.current);
    }

    // Small delay to allow click events to process first
    blurTimeoutRef.current = setTimeout(() => {
      if (isEditing && !isSubmitting) {
        handleSubmit();
      }
      blurTimeoutRef.current = null;
    }, 100);
  }, [isEditing, isSubmitting, handleSubmit]);

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      if (focusTimeoutRef.current) {
        clearTimeout(focusTimeoutRef.current);
      }
      if (blurTimeoutRef.current) {
        clearTimeout(blurTimeoutRef.current);
      }
    };
  }, []);

  if (isEditing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        disabled={isSubmitting}
        className={`bg-white border border-blue-300 rounded-[2px] px-1 py-0.5 text-xs font-medium text-gray-700 focus:outline-none focus:ring-[0.5px] focus:ring-black focus:border-black min-w-0 ${className}`}
        placeholder="Folder name"
        maxLength={100}
      />
    );
  }

  const isRootFolder = folderId === "";

  return (
    <span
      onDoubleClick={handleDoubleClick}
      className={`cursor-pointer select-none ${className}`}
      title={isRootFolder ? "Default folder" : "Double-click to rename"}
    >
      {name || (isRootFolder ? "Default Folder" : "Unnamed")}
    </span>
  );
});

export default EditableFolderName;
