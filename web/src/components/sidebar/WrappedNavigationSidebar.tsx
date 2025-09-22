"use client";

import { BarChart3, Cloud, FileText, Layers, Search, Settings } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { UserButton } from "@/auth/components";
import { HoverPopover } from "@/components/HoverPopover";

interface WrappedNavigationSidebarProps {
  onOpenCommandPalette?: () => void;
  setIsExpanded: (expanded: boolean) => void;
}

export default function WrappedNavigationSidebar({
  onOpenCommandPalette,
  setIsExpanded,
}: WrappedNavigationSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleOpenApiKeysModal = () => {
    const params = new URLSearchParams(searchParams);
    params.set("showManageKeysModal", "true");
    router.push(`${pathname}?${params.toString()}`);
  };

  return (
    <div className="w-16 bg-gray-50 border-r border-gray-200 flex flex-col items-center py-4 gap-2 h-screen">
      {/* Logo that expands sidebar when clicked */}
      <HoverPopover
        content={<span className="text-white text-sm">Expand Sidebar</span>}
        position="right"
        className="flex mb-2"
        popoverClassName="bg-gray-800 rounded-[2px] px-2 py-1"
      >
        <button onClick={() => setIsExpanded(true)} className="cursor-pointer">
          <Image src="/sidebar-logo.png" alt="AnotherAI Logo" width={32} height={32} className="w-8 h-8" />
        </button>
      </HoverPopover>

      {/* Icon-only navigation buttons */}
      <HoverPopover
        content={<span className="text-white text-sm">Search</span>}
        position="right"
        className="flex"
        popoverClassName="bg-gray-800 rounded-[2px] px-2 py-1"
      >
        <button
          onClick={onOpenCommandPalette}
          className="p-3 rounded-md transition-colors text-gray-700 hover:bg-gray-100 cursor-pointer"
        >
          <Search className="w-4 h-4" />
        </button>
      </HoverPopover>

      <HoverPopover
        content={<span className="text-white text-sm">Completions</span>}
        position="right"
        className="flex"
        popoverClassName="bg-gray-800 rounded-[2px] px-2 py-1"
      >
        <Link
          href="/completions"
          className={`p-3 rounded-md transition-colors cursor-pointer ${
            pathname === "/completions" ? "bg-blue-100 text-blue-700" : "text-gray-700 hover:bg-gray-100"
          }`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </Link>
      </HoverPopover>

      <HoverPopover
        content={<span className="text-white text-sm">Agents</span>}
        position="right"
        className="flex"
        popoverClassName="bg-gray-800 rounded-[2px] px-2 py-1"
      >
        <Link
          href="/agents"
          className={`p-3 rounded-md transition-colors cursor-pointer ${
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
        </Link>
      </HoverPopover>

      <HoverPopover
        content={<span className="text-white text-sm">Experiments</span>}
        position="right"
        className="flex"
        popoverClassName="bg-gray-800 rounded-[2px] px-2 py-1"
      >
        <Link
          href="/experiments"
          className={`p-3 rounded-md transition-colors cursor-pointer ${
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
        </Link>
      </HoverPopover>

      <HoverPopover
        content={<span className="text-white text-sm">Metrics</span>}
        position="right"
        className="flex"
        popoverClassName="bg-gray-800 rounded-[2px] px-2 py-1"
      >
        <Link
          href="/metrics"
          className={`p-3 rounded-md transition-colors cursor-pointer ${
            pathname === "/metrics" ? "bg-blue-100 text-blue-700" : "text-gray-700 hover:bg-gray-100"
          }`}
        >
          <BarChart3 className="w-4 h-4" />
        </Link>
      </HoverPopover>

      <HoverPopover
        content={<span className="text-white text-sm">Deployments</span>}
        position="right"
        className="flex"
        popoverClassName="bg-gray-800 rounded-[2px] px-2 py-1"
      >
        <Link
          href="/deployments"
          className={`p-3 rounded-md transition-colors cursor-pointer ${
            pathname.startsWith("/deployments") ? "bg-blue-100 text-blue-700" : "text-gray-700 hover:bg-gray-100"
          }`}
        >
          <Cloud className="w-4 h-4" />
        </Link>
      </HoverPopover>

      <HoverPopover
        content={<span className="text-white text-sm">Manage API Keys</span>}
        position="right"
        className="flex"
        popoverClassName="bg-gray-800 rounded-[2px] px-2 py-1"
      >
        <button
          onClick={handleOpenApiKeysModal}
          className="p-3 rounded-md transition-colors text-gray-700 hover:bg-gray-100 cursor-pointer"
        >
          <Settings className="w-4 h-4" />
        </button>
      </HoverPopover>

      <HoverPopover
        content={<span className="text-white text-sm">Documentation</span>}
        position="right"
        className="flex"
        popoverClassName="bg-gray-800 rounded-[2px] px-2 py-1"
      >
        <a
          href="https://docs.anotherai.dev"
          target="_blank"
          rel="noopener noreferrer"
          className="p-3 rounded-md transition-colors text-gray-700 hover:bg-gray-100 cursor-pointer"
        >
          <FileText className="w-4 h-4" />
        </a>
      </HoverPopover>

      <HoverPopover
        content={<span className="text-white text-sm">Models</span>}
        position="right"
        className="flex"
        popoverClassName="bg-gray-800 rounded-[2px] px-2 py-1"
      >
        <a
          href="https://docs.anotherai.dev/inference/models#list"
          target="_blank"
          rel="noopener noreferrer"
          className="p-3 rounded-md transition-colors text-gray-700 hover:bg-gray-100 cursor-pointer"
        >
          <Layers className="w-4 h-4" />
        </a>
      </HoverPopover>

      {/* User button at bottom - avatar only */}
      <div className="mt-auto pt-2">
        <UserButton avatarOnly={true} />
      </div>
    </div>
  );
}
