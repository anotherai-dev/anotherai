import { ChevronDown, ChevronUp } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import { useKeyboardShortcut } from "@/hooks/useKeyboardShortcut";
import { useStoredCompletionsList } from "@/store/stored_completions";

interface CompletionNavigationButtonsProps {
  completionId: string;
  onNavigateToCompletion?: (targetId: string) => void;
}

export function CompletionNavigationButtons({
  completionId,
  onNavigateToCompletion,
}: CompletionNavigationButtonsProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const storedCompletionsList = useStoredCompletionsList();

  // Default navigation logic for backward compatibility
  const defaultNavigateToCompletion = useCallback(
    (targetId: string) => {
      const params = new URLSearchParams(searchParams);
      params.set("showCompletionModal", targetId);
      const newUrl = `${window.location.pathname}?${params.toString()}`;
      router.replace(newUrl, { scroll: false });
    },
    [searchParams, router]
  );

  const navigateToCompletion = onNavigateToCompletion ?? defaultNavigateToCompletion;

  const navigateUp = useCallback(() => {
    if (!storedCompletionsList || !completionId) return;

    const currentIndex = storedCompletionsList.findIndex((completion) => String(completion.id) === completionId);
    if (currentIndex > 0) {
      const targetCompletion = storedCompletionsList[currentIndex - 1];
      const targetId = String(targetCompletion.id);
      navigateToCompletion(targetId);
    }
  }, [storedCompletionsList, completionId, navigateToCompletion]);

  const navigateDown = useCallback(() => {
    if (!storedCompletionsList || !completionId) return;

    const currentIndex = storedCompletionsList.findIndex((completion) => String(completion.id) === completionId);
    if (currentIndex >= 0 && currentIndex < storedCompletionsList.length - 1) {
      const targetCompletion = storedCompletionsList[currentIndex + 1];
      const targetId = String(targetCompletion.id);
      navigateToCompletion(targetId);
    }
  }, [storedCompletionsList, completionId, navigateToCompletion]);

  // Keyboard shortcuts for navigation
  useKeyboardShortcut(["ArrowUp"], navigateUp);
  useKeyboardShortcut(["ArrowDown"], navigateDown);

  // Don't render if no completions list or empty list
  if (!storedCompletionsList || storedCompletionsList.length === 0) {
    return null;
  }

  // Find current position in the list
  const currentIndex = storedCompletionsList.findIndex((completion) => String(completion.id) === completionId);

  const canNavigateUp = currentIndex > 0;
  const canNavigateDown = currentIndex >= 0 && currentIndex < storedCompletionsList.length - 1;

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={navigateUp}
        disabled={!canNavigateUp}
        className={`border border-gray-200 px-2 py-1 rounded-[2px] w-8 h-8 flex items-center justify-center shadow-sm shadow-black/5 ${
          canNavigateUp
            ? "bg-white text-gray-900 hover:bg-gray-100 cursor-pointer"
            : "bg-gray-100 text-gray-400 cursor-not-allowed"
        }`}
      >
        <ChevronUp size={16} />
      </button>
      <button
        onClick={navigateDown}
        disabled={!canNavigateDown}
        className={`border border-gray-200 px-2 py-1 rounded-[2px] w-8 h-8 flex items-center justify-center shadow-sm shadow-black/5 ${
          canNavigateDown
            ? "bg-white text-gray-900 hover:bg-gray-100 cursor-pointer"
            : "bg-gray-100 text-gray-400 cursor-not-allowed"
        }`}
      >
        <ChevronDown size={16} />
      </button>
    </div>
  );
}
