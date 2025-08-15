import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Annotation } from "@/types/models";
import { useAnnotationActions } from "../../store/annotations";

export type AddAnnotationFormProps = {
  completionId?: string;
  experimentId?: string;
  keyPath?: string;
  keyPathPrefix?: string;
  onCancel: () => void;
  onSuccess?: () => void;
};

export function AddAnnotationForm({
  completionId,
  experimentId,
  keyPath,
  keyPathPrefix,
  onCancel,
  onSuccess,
}: AddAnnotationFormProps) {
  const { addAnnotations } = useAnnotationActions();
  const [annotationText, setAnnotationText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const fullKeyPath = useMemo(() => {
    if (keyPathPrefix && keyPath) {
      return `${keyPathPrefix}.${keyPath}`;
    }
    return keyPath || keyPathPrefix || undefined;
  }, [keyPath, keyPathPrefix]);

  // Focus textarea when keyPath is provided (indicating selection from UI)
  useEffect(() => {
    if (keyPath && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [keyPath]);

  const handleSave = useCallback(async () => {
    if (!annotationText.trim() || isSubmitting) return;

    setIsSubmitting(true);

    const newAnnotation: Annotation = {
      id: `ann_${Date.now()}`, // Temporary ID
      author_name: "User",
      created_at: new Date().toISOString(),
      text: annotationText.trim(),
      target: {
        completion_id: completionId,
        experiment_id: experimentId,
        key_path: fullKeyPath,
      },
      context: experimentId ? { experiment_id: experimentId } : undefined,
    };

    const success = await addAnnotations([newAnnotation]);

    setIsSubmitting(false);

    if (success) {
      setAnnotationText("");
      onSuccess?.();
    } else {
      // Could add error handling UI here - for now just log
      console.error("Failed to add annotation");
    }
  }, [annotationText, isSubmitting, completionId, experimentId, fullKeyPath, addAnnotations, onSuccess]);

  const handleCancel = useCallback(() => {
    setAnnotationText("");
    onCancel();
  }, [onCancel]);

  return (
    <div className="p-2 border rounded-[2px] bg-gray-50 border-gray-200">
      {keyPath && (
        <div className="mb-2">
          <span className="inline-block px-2 py-1 text-xs bg-gray-100 border border-gray-200 text-gray-600 font-medium rounded-[2px] whitespace-nowrap">
            {keyPath}
          </span>
        </div>
      )}
      <textarea
        ref={textareaRef}
        value={annotationText}
        onChange={(e) => setAnnotationText(e.target.value)}
        placeholder="Add an annotation"
        className="w-full text-xs p-2 border border-gray-200 rounded-[2px] resize-none focus:outline-none focus:ring-1 focus:ring-gray-900 focus:border-gray-900 bg-white"
        rows={3}
        disabled={isSubmitting}
      />
      <div className="flex gap-2 mt-2">
        <button
          onClick={handleCancel}
          disabled={isSubmitting}
          className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer px-2 py-1 rounded-[2px] text-xs font-semibold shadow-sm shadow-black/5"
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={!annotationText.trim() || isSubmitting}
          className="bg-gray-600 border border-gray-200 text-white hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer px-2 py-1 rounded-[2px] text-xs font-semibold shadow-sm shadow-black/5"
        >
          {isSubmitting ? "Saving..." : "Add Annotation"}
        </button>
      </div>
    </div>
  );
}
