"use client";

import { HeaderSection } from "@/components/HeaderSection";
import { useOrFetchExperiments } from "@/store/experiments";
import { ExperimentsTable } from "./sections/table/ExperimentsTable";

export default function ExperimentsPage() {
  const { experiments, isLoading, error, total, currentPage, pageSize, setPage } = useOrFetchExperiments();

  return (
    <div className="flex flex-col w-full h-screen overflow-auto">
      <div className="flex-1 mx-auto px-4 py-8 gap-6 bg-gray-50 w-full min-h-full">
        <HeaderSection title="Experiments" description="View and analyze your AI model experiments and results" />

        <div className="mt-6 flex-1 flex flex-col">
          <ExperimentsTable
            experiments={experiments}
            total={total}
            currentPage={currentPage}
            pageSize={pageSize}
            isLoading={isLoading}
            error={error}
            onPageChange={setPage}
          />
        </div>
      </div>
    </div>
  );
}
