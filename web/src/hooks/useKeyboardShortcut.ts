"use client";

import { useEffect } from "react";

export function useKeyboardShortcut(keys: string[], callback: () => void) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const keysPressed: string[] = [];

      if (event.metaKey || event.ctrlKey) keysPressed.push("mod");
      if (event.shiftKey) keysPressed.push("shift");
      if (event.altKey) keysPressed.push("alt");
      keysPressed.push(event.key.toLowerCase());

      const targetKeys = keys.map((key) => key.toLowerCase());

      if (keysPressed.length === targetKeys.length && targetKeys.every((key) => keysPressed.includes(key))) {
        event.preventDefault();
        callback();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [keys, callback]);
}
