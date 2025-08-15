"use client";

import * as Toast from "@radix-ui/react-toast";
import { Check } from "lucide-react";
import { ReactNode, createContext, useContext, useState } from "react";

interface ToastContextType {
  showToast: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

interface ToastProviderProps {
  children: ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");

  const showToast = (msg: string) => {
    setMessage(msg);
    setOpen(true);
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <Toast.Provider swipeDirection="right">
        <Toast.Root
          className="bg-green-600 text-white rounded-[2px] shadow-lg p-3 flex items-center gap-2 animate-slideIn data-[state=closed]:animate-hide"
          open={open}
          onOpenChange={setOpen}
          duration={2000}
        >
          <Check size={16} className="text-white" />
          <Toast.Title className="text-sm font-medium text-white">{message}</Toast.Title>
        </Toast.Root>
        <Toast.Viewport className="fixed bottom-4 left-1/2 transform -translate-x-1/2 flex flex-col gap-2 max-w-[100vw] m-0 list-none z-[2147483647] outline-none" />
      </Toast.Provider>
    </ToastContext.Provider>
  );
}
