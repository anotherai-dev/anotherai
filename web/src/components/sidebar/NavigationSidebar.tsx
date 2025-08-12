"use client";

import { ChevronLeft, Search } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import ViewsSection from "@/components/sidebar/ViewsSection";

interface NavigationSidebarProps {
  onOpenCommandPalette?: () => void;
}

export default function NavigationSidebar({
  onOpenCommandPalette,
}: NavigationSidebarProps = {}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const pathname = usePathname();

  if (!isExpanded) {
    return (
      <div className="w-16 bg-gray-50 border-r border-gray-200 flex flex-col items-center py-4">
        <button
          onClick={() => setIsExpanded(true)}
          className="mb-4 cursor-pointer"
          title="Expand sidebar"
        >
          <Image
            src="/sidebar-logo.png"
            alt="AnotherAI Logo"
            width={32}
            height={32}
            className="w-8 h-8"
          />
        </button>
      </div>
    );
  }

  return (
    <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col h-screen">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* AnotherAI Logo */}
          <Image
            src="/sidebar-logo.png"
            alt="AnotherAI Logo"
            width={32}
            height={32}
            className="w-8 h-8"
          />
          <span className="font-semibold text-gray-900">AnotherAI</span>
        </div>
        <div className="flex items-center gap-1">
          {onOpenCommandPalette && (
            <button
              onClick={onOpenCommandPalette}
              className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors cursor-pointer"
              title="Open command palette (⌘K)"
            >
              <Search className="w-5 h-5" />
            </button>
          )}
          <button
            onClick={() => setIsExpanded(false)}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors cursor-pointer"
            title="Collapse sidebar"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="p-3 border-b border-gray-200">
        <button
          onClick={onOpenCommandPalette}
          className="w-full flex items-center gap-3 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors group cursor-pointer"
        >
          <Search className="w-4 h-4 text-gray-400 group-hover:text-gray-500" />
          <span className="text-sm text-gray-500 group-hover:text-gray-600">
            Search
          </span>
          <div className="ml-auto flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 text-xs font-semibold text-gray-500 bg-white border border-gray-300 rounded">
              ⌘
            </kbd>
            <kbd className="px-1.5 py-0.5 text-xs font-semibold text-gray-500 bg-white border border-gray-300 rounded">
              K
            </kbd>
          </div>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Main Navigation */}
        <div className="p-2 border-b border-gray-200">
          <Link
            href="/completions"
            className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors mb-1 ${
              pathname === "/completions"
                ? "bg-blue-100 text-blue-700"
                : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 12h14M12 5l7 7-7 7"
              />
            </svg>
            Completions
          </Link>

          <Link
            href="/experiments"
            className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors mb-1 ${
              pathname === "/experiments"
                ? "bg-blue-100 text-blue-700"
                : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
              />
            </svg>
            Experiments
          </Link>

          <Link
            href="/agents"
            className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors mb-1 ${
              pathname === "/agents"
                ? "bg-blue-100 text-blue-700"
                : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
            Agents
          </Link>

          <a
            href="https://github.com/anotherai-dev/anotherai"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors mb-1 text-gray-700 hover:bg-gray-100"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            MCP Set Up
          </a>
        </div>

        <ViewsSection />
      </div>
    </div>
  );
}
