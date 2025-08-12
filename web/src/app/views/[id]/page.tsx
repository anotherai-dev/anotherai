"use client";

import { Info } from "lucide-react";
import { useParams } from "next/navigation";
import { SearchSection } from "@/app/completions/sections/SearchSection";
import { CompletionsTable } from "@/app/completions/sections/table/CompletionsTable";
import ErrorState from "@/components/ErrorState";
import { HoverPopover } from "@/components/HoverPopover";
import LoadingState from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { CompletionsGraph } from "@/components/universal-charts/CompletionsGraph";
import { useCompletionsListSync } from "@/hooks/useCompletionsListSync";
import { useCompletionsQuery } from "@/store/completions";
import { useOrFetchView } from "@/store/views";
import { EditViewTooltip } from "./components/EditViewTooltip";

export default function ViewPage() {
  const params = useParams();
  const viewId = params.id as string;

  const { view, isLoading, error, update } = useOrFetchView(viewId);

  // Use completions query for table views
  const {
    data,
    isLoading: isQueryLoading,
    error: queryError,
  } = useCompletionsQuery(view?.query || "");

  // Sync completions data with stored completions list for modal navigation
  useCompletionsListSync(data);

  if (error) {
    return <ErrorState error={error?.message} onRetry={update} />;
  }

  if (!view || isLoading) {
    return <LoadingState />;
  }

  return (
    <div className="flex flex-col w-full h-full mx-auto px-4 py-8 gap-6 bg-gray-50">
      <PageHeader
        breadcrumbs={[{ label: "Views" }, { label: view.title }]}
        title={view.title}
        copyablePrefixAndId={`anotherai/view/${viewId}`}
        className=""
        rightContent={
          <HoverPopover
            content={<EditViewTooltip viewId={viewId} />}
            position="bottom"
            popoverClassName="bg-gray-900 rounded-md overflow-hidden px-2 py-1"
          >
            <button className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer px-3 py-1 rounded-[2px] text-sm shadow-sm shadow-black/5 flex items-center gap-2">
              <Info size={14} />
              Edit View
            </button>
          </HoverPopover>
        }
      />

      <HoverPopover
        content={<EditViewTooltip viewId={viewId} />}
        position="bottomLeft"
        popoverClassName="bg-gray-900 rounded-md overflow-hidden px-2 py-1"
      >
        <SearchSection
          defaultValue={view.query || ""}
          placeholder="Enter SQL query to search view data..."
          isLoading={false}
          readOnly={true}
        />
      </HoverPopover>

      {view.graph &&
      ["bar", "line", "pie", "scatter"].includes(view.graph.type) ? (
        <CompletionsGraph
          data={data ?? []}
          isLoading={isQueryLoading}
          error={queryError ? { error: queryError.message } : null}
          graph={view.graph}
          title={view.title}
        />
      ) : (
        <CompletionsTable
          data={data ?? []}
          isLoading={isQueryLoading}
          error={queryError}
        />
      )}
    </div>
  );
}
