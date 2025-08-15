"use client";

import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import { useViews } from "@/store/views";

interface EditableViewTitleProps {
  viewId: string;
  title: string;
  className?: string;
  onEditingChange?: (isEditing: boolean) => void;
}

export interface EditableViewTitleRef {
  startEditing: () => void;
}

const EditableViewTitle = forwardRef<EditableViewTitleRef, EditableViewTitleProps>(function EditableViewTitle(
  { viewId, title, className = "", onEditingChange },
  ref
) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(title);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const focusTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const { patchView } = useViews();

  const startEditing = useCallback(() => {
    setIsEditing(true);
  }, []);

  // Notify parent when editing state changes
  useEffect(() => {
    onEditingChange?.(isEditing);
  }, [isEditing, onEditingChange]);

  useImperativeHandle(
    ref,
    () => ({
      startEditing,
    }),
    [startEditing]
  );

  // Reset edit value when title changes from outside
  useEffect(() => {
    if (!isEditing) {
      setEditValue(title);
    }
  }, [title, isEditing]);

  // Focus input when entering edit mode
  useEffect(() => {
    if (isEditing && inputRef.current) {
      // Clear any existing timeout
      if (focusTimeoutRef.current) {
        clearTimeout(focusTimeoutRef.current);
      }

      // Small delay to ensure input is rendered and menu is closed
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

  const handleDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation(); // Prevent navigation when double-clicking to edit
      startEditing();
    },
    [startEditing]
  );

  const handleSubmit = useCallback(async () => {
    if (isSubmitting || editValue.trim() === title.trim()) {
      setIsEditing(false);
      setEditValue(title);
      return;
    }

    const trimmedValue = editValue.trim();
    if (!trimmedValue) {
      setEditValue(title);
      setIsEditing(false);
      return;
    }

    setIsSubmitting(true);
    try {
      await patchView(viewId, { title: trimmedValue });
      setIsEditing(false);
    } catch (error) {
      console.error("Failed to update view title:", error);
      // Reset to original title on error
      setEditValue(title);
      setIsEditing(false);
    } finally {
      setIsSubmitting(false);
    }
  }, [viewId, editValue, title, patchView, isSubmitting]);

  const handleCancel = useCallback(() => {
    setEditValue(title);
    setIsEditing(false);
  }, [title]);

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
    // Small delay to allow click events to process first
    setTimeout(() => {
      if (isEditing && !isSubmitting) {
        handleSubmit();
      }
    }, 200);
  }, [isEditing, isSubmitting, handleSubmit]);

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
        className={`bg-white border border-blue-300 rounded-[2px] px-1 py-0.5 text-xs font-normal text-gray-900 focus:outline-none focus:ring-[0.5px] focus:ring-black focus:border-black min-w-0 flex-1 ${className}`}
        placeholder="View title"
        maxLength={200}
      />
    );
  }

  return (
    <span
      onDoubleClick={handleDoubleClick}
      className={`cursor-pointer select-none flex-1 break-words ${className}`}
      title="Double-click to rename"
    >
      {title}
    </span>
  );
});

export default EditableViewTitle;
