import { create } from "zustand";

interface StoredCompletionsState {
  storedCompletionsList: Record<string, unknown>[]; // Stored completions list for navigation

  setStoredCompletionsList: (completions: Record<string, unknown>[]) => void;
  clearStoredCompletionsList: () => void;
}

export const useStoredCompletions = create<StoredCompletionsState>((set) => ({
  storedCompletionsList: [],

  setStoredCompletionsList: (completions: Record<string, unknown>[]) => {
    set({ storedCompletionsList: completions });
  },

  clearStoredCompletionsList: () => {
    set({ storedCompletionsList: [] });
  },
}));

export const useStoredCompletionsList = () => {
  return useStoredCompletions((state) => state.storedCompletionsList);
};
