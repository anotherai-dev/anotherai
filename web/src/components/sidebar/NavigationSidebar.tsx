"use client";

import { BarChart3, ChevronLeft, Cloud, FileText, Layers, Search, Settings } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ApiKeysButton, CreditsSection, UserButton } from "@/auth/components";
import ViewsSection from "@/components/sidebar/ViewsSection";
import WrappedNavigationSidebar from "@/components/sidebar/WrappedNavigationSidebar";
import { useCookieState } from "@/hooks/useCookieState";

interface NavigationSidebarProps {
  onOpenCommandPalette?: () => void;
  initialExpanded?: boolean;
}

export default function NavigationSidebar({ onOpenCommandPalette, initialExpanded = true }: NavigationSidebarProps) {
  const [isExpanded, setIsExpanded] = useCookieState("sidebar-expanded", initialExpanded);
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleOpenApiKeysModal = () => {
    const params = new URLSearchParams(searchParams);
    params.set("showManageKeysModal", "true");
    router.push(`${pathname}?${params.toString()}`);
  };

  if (!isExpanded) {
    return <WrappedNavigationSidebar onOpenCommandPalette={onOpenCommandPalette} setIsExpanded={setIsExpanded} />;
  }

  return (
    <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col h-screen">
      {/* Header */}
      <div className="py-4 pl-3 pr-2 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* AnotherAI Logo */}
          <Image src="/sidebar-logo.png" alt="AnotherAI Logo" width={32} height={32} className="w-8 h-8" />
          <span className="font-semibold text-gray-900">AnotherAI</span>
        </div>
        <div className="flex items-center gap-1">
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
      <div className="py-3 px-2 border-b border-gray-200">
        <button
          onClick={onOpenCommandPalette}
          className="w-full flex items-center gap-3 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-[4px] transition-colors group cursor-pointer"
        >
          <Search className="w-4 h-4 text-gray-400 group-hover:text-gray-500" />
          <span className="text-sm text-gray-500 group-hover:text-gray-600">Search</span>
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
            className={`flex items-center gap-3 px-3 py-2 rounded-[4px] text-sm transition-colors mb-[2px] cursor-pointer ${
              pathname === "/completions" ? "bg-blue-100 text-blue-700" : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
            </svg>
            Completions
          </Link>
          <Link
            href="/agents"
            className={`flex items-center gap-3 px-3 py-2 rounded-[4px] text-sm transition-colors mb-[2px] cursor-pointer ${
              pathname === "/agents" ? "bg-blue-100 text-blue-700" : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
            Agents
          </Link>
          <Link
            href="/experiments"
            className={`flex items-center gap-3 px-3 py-2 rounded-[4px] text-sm transition-colors mb-[2px] cursor-pointer ${
              pathname === "/experiments" ? "bg-blue-100 text-blue-700" : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
            href="/metrics"
            className={`flex items-center gap-3 px-3 py-2 rounded-[4px] text-sm transition-colors mb-[2px] cursor-pointer ${
              pathname === "/metrics" ? "bg-blue-100 text-blue-700" : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            Metrics
          </Link>
          <Link
            href="/deployments"
            className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors mb-1 cursor-pointer ${
              pathname.startsWith("/deployments") ? "bg-blue-100 text-blue-700" : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <Cloud className="w-4 h-4" />
            Deployments
          </Link>
          <ApiKeysButton onClick={handleOpenApiKeysModal} />
          <a
            href="https://docs.anotherai.dev/getting-started"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 px-3 py-2 rounded-[4px] text-sm transition-colors mb-1 text-gray-700 hover:bg-gray-100 cursor-pointer"
          >
            <Settings className="w-4 h-4" />
            MCP Set Up
          </a>
          <a
            href="https://docs.anotherai.dev"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 px-3 py-2 rounded-[4px] text-sm transition-colors mb-1 text-gray-700 hover:bg-gray-100 cursor-pointer"
          >
            <FileText className="w-4 h-4" />
            Documentation
          </a>
          <a
            href="https://docs.anotherai.dev/features/models"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 px-3 py-2 rounded-[4px] text-sm transition-colors mb-1 text-gray-700 hover:bg-gray-100 cursor-pointer"
          >
            <Layers className="w-4 h-4" />
            Models
          </a>
        </div>

        <ViewsSection />

        {/* Auto-refresh indicator */}
        <div className="px-3 py-3 border-t border-gray-200">
          <p className="text-xs text-gray-400 text-center">Views update automatically</p>
        </div>

        <UserButton className="border-t border-gray-200" />
        <CreditsSection />
      </div>
    </div>
  );
}
