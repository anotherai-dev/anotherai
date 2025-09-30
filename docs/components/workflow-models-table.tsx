"use client";

interface ModelSupports {
  input: {
    image: boolean;
    audio: boolean;
    pdf: boolean;
    text: boolean;
  };
  output: {
    image: boolean;
    audio: boolean;
    pdf: boolean;
    text: boolean;
  };
  parallel_tool_calls: boolean;
  tools: boolean;
  top_p: boolean;
  temperature: boolean;
}

interface ModelPricing {
  input_token_usd: number;
  output_token_usd: number;
}

interface ContextWindow {
  max_tokens: number;
  max_output_tokens: number;
}

interface Model {
  id: string;
  object: string;
  created: number;
  owned_by: string;
  display_name: string;
  icon_url: string;
  supports: ModelSupports;
  pricing: ModelPricing;
  release_date: string;
  context_window: ContextWindow;
}

interface WorkflowModelsTableProps {
  models: Model[];
}

export function WorkflowModelsTable({ models }: WorkflowModelsTableProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const formatPrice = (price: number) => {
    // Convert to price per million tokens
    const pricePerMillion = price * 1000000;
    return `$${pricePerMillion.toFixed(2)}`;
  };

  const formatContextWindow = (tokens: number) => {
    if (tokens >= 1000000) {
      return `${(tokens / 1000000).toFixed(1)}M`;
    } else if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(0)}K`;
    }
    return tokens.toString();
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left p-2 font-semibold" style={{ minWidth: "50px" }}></th>
            <th className="text-left p-2 font-semibold">Model ID</th>
            <th className="text-left p-2 font-semibold">Input Price</th>
            <th className="text-left p-2 font-semibold">Output Price</th>
            <th className="text-left p-2 font-semibold">Context Window</th>
            <th className="text-left p-2 font-semibold">Release Date</th>
          </tr>
        </thead>
        <tbody>
          {models.map((model) => (
            <tr key={model.id} className="border-b border-border hover:bg-accent/50 transition-colors">
              <td className="p-2">
                {model.icon_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={model.icon_url} alt={model.owned_by} className="w-6 h-6" />
                )}
              </td>
              <td className="p-2">
                <code className="text-sm">{model.id}</code>
              </td>
              <td className="p-2 text-sm">
                <span className="font-mono">{formatPrice(model.pricing.input_token_usd)}</span>
                <span className="text-xs text-muted-foreground ml-1">/ 1M tokens</span>
              </td>
              <td className="p-2 text-sm">
                <span className="font-mono">{formatPrice(model.pricing.output_token_usd)}</span>
                <span className="text-xs text-muted-foreground ml-1">/ 1M tokens</span>
              </td>
              <td className="p-2 text-sm font-mono">{formatContextWindow(model.context_window.max_tokens)}</td>
              <td className="p-2 text-sm text-muted-foreground">{formatDate(model.release_date)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
