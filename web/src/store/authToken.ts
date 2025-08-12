import { create } from "zustand";

interface AuthTokenState {
  token: string | null;
  setToken: (token: string | null) => void;
}

export const useAuthToken = create<AuthTokenState>()((set) => ({
  token: null,
  setToken: (token) => set({ token }),
}));
