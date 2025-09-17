"use client";

import { useParams } from "next/navigation";
import { SearchSection } from "@/app/completions/sections/SearchSection";
import ErrorState from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { CompletionsGraph } from "@/components/universal-charts/CompletionsGraph";
import { useCompletionsQuery } from "@/store/completions";
import { useOrFetchViewFolders, useViewFolder } from "@/store/views";
import { View } from "@/types/models";

export default function FolderPage() {
  const params = useParams();
  const folderId = params.id as string;

  const { error: foldersError, update } = useOrFetchViewFolders();
  const folder = useViewFolder(folderId);

  if (foldersError) {
    return <ErrorState error={foldersError?.message} onRetry={update} />;
  }

  if (!folder) {
    return <LoadingState />;
  }

  const viewsWithGraphs = folder.views.filter(
    (view) => view.graph && ["bar", "line", "pie", "scatter"].includes(view.graph.type)
  );

  return (
    <div className="flex flex-col w-full h-full mx-auto px-4 pt-4 pb-8 gap-4 bg-gray-50 overflow-y-auto">
      <PageHeader
        breadcrumbs={[{ label: "Views" }, { label: folder.name }]}
        title={folder.name}
        copyablePrefixAndId={`anotherai/folder/${folderId}`}
        className="pb-0"
      />

      {viewsWithGraphs.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-[4px] p-6 shadow-sm">
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <p className="text-lg">No graph views found in this folder</p>
            <p className="text-sm mt-2">Views with graphs will be displayed here</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {viewsWithGraphs.map((view) => (
            <FolderViewGraph key={view.id} view={view} />
          ))}
        </div>
      )}
    </div>
  );
}

function FolderViewGraph({ view }: { view: View }) {
  const { data, isLoading, error } = useCompletionsQuery(view.query || "");

  return (
    <div className="bg-white border border-gray-200 rounded-[2px] flex flex-col shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">{view.title}</h3>
        <SearchSection
          defaultValue={view.query || ""}
          placeholder="Enter SQL query to search view data..."
          isLoading={false}
          readOnly={true}
        />
      </div>

      {/* Graph Content */}
      <div className="flex-1">
        <CompletionsGraph
          data={data ?? []}
          isLoading={isLoading}
          error={error ? { error: error.message } : null}
          graph={view.graph}
          title={view.title}
          showBorder={false}
        />
      </div>
    </div>
  );
}
