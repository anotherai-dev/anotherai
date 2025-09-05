"use client";

import { Command } from "cmdk";
import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo } from "react";
import { useOrFetchAgentsWithCounts } from "@/store/agents_with_counts";
import { useAllViews, useOrFetchViewFolders } from "@/store/views";
import { View } from "@/types/models";
import { AgentsGroup } from "./command-palette/AgentsGroup";
import { NavigationGroup } from "./command-palette/NavigationGroup";
import { ViewsGroup } from "./command-palette/ViewsGroup";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

const navigationItems = [
  {
    id: "completions",
    name: "Completions",
    description: "View and search completions",
    href: "/completions",
    icon: () => (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
      </svg>
    ),
    keywords: ["completions", "runs", "executions", "logs"],
  },
  {
    id: "experiments",
    name: "Experiments",
    description: "Manage and review experiments",
    href: "/experiments",
    icon: () => (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
        />
      </svg>
    ),
    keywords: ["experiments", "tests", "comparisons"],
  },
  {
    id: "agents",
    name: "Agents",
    description: "Manage and view agents",
    href: "/agents",
    icon: () => (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
        />
      </svg>
    ),
    keywords: ["agents", "bots", "models"],
  },
];

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const router = useRouter();

  // Fetch data
  const { viewFolders, isLoading: isLoadingViews } = useOrFetchViewFolders();
  const { agents, isLoading: isLoadingAgents } = useOrFetchAgentsWithCounts();
  const views = useAllViews();

  // Memoized computed values
  const viewsByFolder = useMemo(() => {
    return viewFolders.reduce(
      (acc, folder) => {
        if (folder.views && folder.views.length > 0) {
          acc[folder.id] = {
            name: folder.name,
            views: folder.views,
          };
        }
        return acc;
      },
      {} as Record<string, { name: string; views: View[] }>
    );
  }, [viewFolders]);

  const isLoading = isLoadingViews || isLoadingAgents;

  // Handle ESC key to close modal
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown, true); // Use capture phase
    return () => document.removeEventListener("keydown", handleKeyDown, true);
  }, [isOpen, onClose]);

  const handleSelect = useCallback(
    (value: string) => {
      if (value.startsWith("nav:")) {
        const navId = value.replace("nav:", "");
        const navItem = navigationItems.find((item) => item.id === navId);
        if (navItem) {
          router.push(navItem.href);
        }
      } else if (value.startsWith("view:")) {
        const viewId = value.replace("view:", "");
        const view = views.find((v) => v.id === viewId);
        if (view) {
          router.push(`/views/${view.id}`);
        }
      } else if (value.startsWith("agent:")) {
        const agentId = value.replace("agent:", "");
        router.push(`/agents/${agentId}`);
      }
      onClose();
    },
    [router, views, onClose]
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/20 backdrop-blur-sm" onClick={onClose}>
      <div className="flex items-start justify-center pt-[10vh]">
        <div className="w-full max-w-xl" onClick={(e) => e.stopPropagation()}>
          <Command
            className="bg-white rounded-lg shadow-2xl border border-gray-200"
            shouldFilter={true}
            filter={(value, search) => {
              // Custom filter function for better search
              if (!search) return 1;

              const searchLower = search.toLowerCase();
              const valueLower = value.toLowerCase();

              // Extract the actual content (remove prefixes like "nav:" or "view:")
              const cleanValue = valueLower.replace(/^(nav:|view:)[^\s]*\s/, "");

              // Exact match gets highest score
              if (cleanValue.includes(searchLower)) {
                if (cleanValue.startsWith(searchLower)) return 1;
                return 0.8;
              }

              // Word boundary matches
              const words = searchLower.split(" ");
              const valueWords = cleanValue.split(" ");

              let matchedWords = 0;
              words.forEach((word) => {
                if (valueWords.some((vw) => vw.includes(word))) {
                  matchedWords++;
                }
              });

              const matchRatio = matchedWords / words.length;
              return matchRatio > 0.5 ? matchRatio * 0.6 : 0;
            }}
          >
            <div className="flex items-center border-b border-gray-200 px-3">
              <Search className="w-4 h-4 text-gray-400 mr-3" />
              <Command.Input
                placeholder="Type a command or search..."
                className="flex-1 py-3 text-sm bg-transparent border-0 outline-none placeholder-gray-400"
                autoFocus
              />
            </div>

            <Command.List className="max-h-80 overflow-y-auto p-2">
              <Command.Empty className="flex items-center justify-center py-6 text-sm text-gray-500">
                {isLoading ? "Loading..." : "No results found."}
              </Command.Empty>

              <NavigationGroup items={navigationItems} onSelect={handleSelect} />
              <AgentsGroup agents={agents} onSelect={handleSelect} />
              <ViewsGroup viewsBySection={viewsByFolder} onSelect={handleSelect} />
            </Command.List>

            <div className="border-t border-gray-200 px-3 py-2 text-xs text-gray-500 bg-gray-50 rounded-b-lg">
              <div className="flex justify-between">
                <span>Navigate with arrows</span>
                <span>⏎ to select • ⌘K to close</span>
              </div>
            </div>
          </Command>
        </div>
      </div>
    </div>
  );
}
