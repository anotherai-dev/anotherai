"use client";

import { UserButton } from "./auth/UserButton";

export function UserMenu() {
  return (
    <div className="w-full flex gap-1 pl-3 pr-2 py-2 justify-between items-center hover:bg-gray-100 border-b border-gray-200 cursor-pointer rounded-t-sm transition-colors">
      <UserButton />
    </div>
  );
}
