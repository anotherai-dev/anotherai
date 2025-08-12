"use client";

import { BarChart3, Table } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useCallback } from "react";
import { View } from "@/types/models";
import ViewMenuButton from "./ViewMenuButton";

interface ViewCellProps {
  view: View & { folder_id?: string; view_type: "run_list" | "metric" };
}

export default function ViewCell({ view }: ViewCellProps) {
  const router = useRouter();
  const pathname = usePathname();

  const handleViewClick = useCallback(() => {
    const viewId = view.id || "view";
    router.push(`/views/${viewId}`);
  }, [router, view.id]);

  const isActive = useCallback(() => {
    const expectedPath = `/views/${view.id}`;
    return pathname === expectedPath;
  }, [pathname, view.id]);

  return (
    <div className="relative group">
      <div
        className={`flex items-start rounded-md text-xs transition-colors relative ${
          isActive()
            ? "bg-blue-100 text-blue-700"
            : "text-gray-700 hover:bg-gray-100"
        }`}
      >
        <button
          onClick={handleViewClick}
          className="flex-1 text-left px-3 py-2 min-w-0"
        >
          <div className="flex items-start gap-2 min-w-0">
            {view.view_type === "run_list" ? (
              <Table className="w-4 h-4 flex-shrink-0 mt-0.5" />
            ) : (
              <BarChart3 className="w-4 h-4 flex-shrink-0 mt-0.5" />
            )}
            <span className="pr-8 flex-1 break-words">{view.title}</span>
          </div>
        </button>

        <ViewMenuButton
          viewId={view.id}
          viewName={view.title}
          isActive={isActive()}
        />
      </div>
    </div>
  );
}
