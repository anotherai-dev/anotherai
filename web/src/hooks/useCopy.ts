import { useCallback } from "react";
import { useToast } from "@/components/ToastProvider";

export function useCopy() {
  const { showToast } = useToast();

  const copyToClipboard = useCallback(
    async (text: string) => {
      try {
        await navigator.clipboard.writeText(text);
        showToast("Copied to clipboard");
        return true;
      } catch (err) {
        console.error("Failed to copy: ", err);
        showToast("Failed to copy");
        return false;
      }
    },
    [showToast]
  );

  return { copyToClipboard };
}
