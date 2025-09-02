"use client";

import { useParams } from "next/navigation";
import ErrorState from "@/components/ErrorState";
import LoadingState from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { ImproveAgentAnnotationsInstructions } from "@/components/experiment/ImproveAgentAnnotationsInstructions";
import { useOrFetchAnnotations } from "@/store/annotations";
import { useOrFetchExperiment } from "@/store/experiment";
import { OriginalResultsSection } from "./sections/OriginalResultsSection";
import { MatrixSection } from "./sections/Results/MatrixSection";
import { MatchingSection } from "./sections/matching/MatchingSection";

export default function ExperimentDetailPage() {
  const params = useParams();
  const experimentId = params.id as string;

  const {
    experiment,
    isLoading: isLoadingExperiment,
    error: experimentError,
    update,
  } = useOrFetchExperiment(experimentId);

  // Fetch annotations for this experiment
  const { annotations } = useOrFetchAnnotations({
    experiment_id: experimentId,
  });

  if (experimentError) {
    return <ErrorState error={experimentError?.message} onRetry={update} />;
  }

  if (!experiment || isLoadingExperiment) {
    return <LoadingState />;
  }

  return (
    <div className="min-h-screen bg-white">
      <div className="container mx-auto px-4 py-8">
        <PageHeader
          breadcrumbs={[{ label: "Experiments", href: "/experiments" }, { label: experiment.id }]}
          title={experiment.title}
          description={experiment.description}
          copyablePrefixAndId={`anotherai/experiment/${experimentId}`}
          descriptionBottomContent={<ImproveAgentAnnotationsInstructions agentId={experiment.agent_id} />}
        />
        <OriginalResultsSection experiment={experiment} />
        <MatrixSection experiment={experiment} annotations={annotations} />
        <MatchingSection experiment={experiment} annotations={annotations} experimentId={experimentId} />
      </div>
    </div>
  );
}
