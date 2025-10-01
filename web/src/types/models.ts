export interface ModelWithID {
  id: string;
}

// Payment-related types
export interface PaymentMethodResponse {
  payment_method_id: string;
  payment_method_currency?: string;
  last4: string;
  brand: string;
  exp_month: number;
  exp_year: number;
}

export interface PaymentMethodRequest {
  payment_method_id: string;
  payment_method_currency?: string;
}

export interface PaymentMethodIdResponse {
  payment_method_id: string;
}

export interface CreatePaymentIntentRequest {
  amount: number;
}

export interface PaymentIntentCreatedResponse {
  client_secret: string;
  payment_intent_id: string;
}

export interface AutomaticPaymentRequest {
  opt_in: boolean;
  threshold?: number | null;
  balance_to_maintain?: number | null;
}

export interface PaymentFailure {
  failure_date: string;
  failure_code: "payment_failed" | "internal";
  failure_reason: string;
}

export interface OrganizationSettings {
  id: string;
  name?: string;
  slug?: string;
  current_credits_usd?: number;
  added_credits_usd?: number;
  automatic_payment_enabled?: boolean;
  automatic_payment_threshold?: number | null;
  automatic_payment_balance_to_maintain?: number | null;
  payment_failure?: PaymentFailure | null;
  locked_for_payment?: boolean | null;
  stripe_customer_id?: string | null;
}

export interface Tool {
  name: string;
  description?: string;
  input_schema: Record<string, unknown>;
}

export interface ToolCallRequest {
  id: string;
  name: string;
  arguments?: Record<string, unknown>;
}

export interface ToolCallResult {
  id: string;
  output: unknown;
  error?: string;
}

export interface File {
  content_type?: string;
  data?: string;
  url?: string;
  format?: string;
  storage_url?: string;
}

export interface MessageContent {
  text?: string;
  object?: Record<string, unknown> | unknown[];
  image_url?: string;
  audio_url?: string;
  file?: File;
  tool_call_request?: ToolCallRequest;
  tool_call_result?: ToolCallResult;
  reasoning?: string;
}

export interface Message {
  role: "system" | "user" | "assistant" | "developer" | "tool";
  content: MessageContent[] | string | Record<string, unknown>;
  cost_usd?: number;
  duration_seconds?: number;
  metrics?: Array<{ key: string; average: number }>;
}

export interface OutputSchema {
  id: string;
  json_schema: Record<string, unknown>;
}

export interface Version {
  id: string;
  model: string;
  temperature: number;
  top_p: number;
  tools?: Tool[];
  prompt?: Message[];
  input_variables_schema?: Record<string, unknown>;
  output_schema?: OutputSchema;
  reasoning_effort?: "disabled" | "low" | "medium" | "high";
  reasoning_budget?: number;
}

// Extended version type to include optional properties with defaults
export interface ExtendedVersion extends Version {
  use_cache?: string | boolean;
  max_tokens?: number | string;
  stream?: boolean;
  include_usage?: boolean;
  presence_penalty?: number;
  frequency_penalty?: number;
  stop?: string | string[];
  tool_choice?: string | object;
}

export interface Error {
  error: string;
}

export interface Input {
  id: string;
  messages?: Message[];
  variables?: Record<string, unknown>;
}

export interface Output {
  messages?: Message[];
  error?: Error;
}

export interface InferenceUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

export interface LLMTrace {
  kind: "llm";
  duration_seconds: number;
  cost_usd: number;
  model: string;
  provider: string;
  usage?: InferenceUsage;
}

export interface ToolTrace {
  kind: "tool";
  duration_seconds: number;
  cost_usd: number;
  name: string;
  tool_input_preview: string;
  tool_output_preview: string;
}

export type Trace = LLMTrace | ToolTrace;

export interface Annotation {
  id: string;
  created_at: string;
  updated_at?: string;
  author_name: string;
  target?: {
    completion_id?: string;
    experiment_id?: string;
    key_path?: string;
  };
  context?: {
    experiment_id?: string;
  };
  text?: string;
  metric?: {
    name: "accuracy" | "precision" | "mse" | "rmse" | "mae" | "time_to_first_token" | "user_feedback" | string;
    value: number;
  };
  metadata?: Record<string, unknown>;
}

export interface ExperimentCompletion {
  id: string;
  input: ModelWithID;
  version: ModelWithID;
  output: Output;
  cost_usd: number;
  duration_seconds: number;
}

export interface Completion {
  id: string;
  agent_id: string;
  created_at?: string;
  version: Version;
  conversation_id?: string;
  input: Input;
  output: Output;
  messages: Message[];
  annotations?: Annotation[];
  metadata: Record<string, unknown>;
  cost_usd: number;
  duration_seconds?: number;
  traces?: Trace[];
}

export interface Experiment {
  id: string;
  created_at: string;
  updated_at?: string;
  author_name: string;
  title: string;
  description: string;
  result?: string;
  agent_id: string;
  completions: ExperimentCompletion[];
  versions: Version[];
  inputs: Input[];
  annotations?: Annotation[];
  metadata?: Record<string, unknown>;
}

export interface Page<T> {
  items: T[];
  total: number;
  next_page_token?: string;
  previous_page_token?: string;
}

export interface AgentWithCompletionCount {
  agent_id: string;
  completion_count: number;
}

// Utility types for working with experiment data
export type ExperimentWithLookups = Experiment & {
  versionMap: Map<string, Version>;
  inputMap: Map<string, Input>;
  completionMap: Map<string, ExperimentCompletion>;
};

// Helper function to create lookup maps for efficient access
export function createExperimentWithLookups(experiment: Experiment): ExperimentWithLookups {
  const versionMap = new Map(experiment.versions.map((v) => [v.id, v]));
  const inputMap = new Map(experiment.inputs.map((i) => [i.id, i]));
  const completionMap = new Map(experiment.completions.map((c) => [c.id, c]));

  return {
    ...experiment,
    versionMap,
    inputMap,
    completionMap,
  };
}

// Dashboard types
export interface TableGraph {
  type: "table";
}

export interface Axis {
  field: string;
  unit?: string;
  label?: string;
}

export interface YAxis {
  field: string;
  unit?: string;
  label?: string;
  color_hex?: string;
}

export interface BarGraph {
  type: "bar";
  x: Axis;
  y: YAxis[];
  stacked?: boolean;
}

export interface LineGraph {
  type: "line";
  x: Axis;
  y: YAxis[];
}

export interface PieGraph {
  type: "pie";
  x: Axis;
  y: YAxis[];
}

export interface ScatterGraph {
  type: "scatter";
  x: Axis;
  y: YAxis[];
}

export type Graph = TableGraph | BarGraph | LineGraph | PieGraph | ScatterGraph;

export interface View {
  id: string;
  title: string;
  query: string;
  graph?: Graph;
}

export interface DashboardSection {
  id: string;
  title: string;
  views: View[];
}

export interface Dashboard {
  id: string;
  title: string;
  description: string;
  sections?: DashboardSection[];
}

export interface PatchDashboardRequest {
  title?: string;
  description?: string;
}

export interface ViewFolder {
  id: string;
  name: string;
  views: View[];
}

export interface CreateViewRequest extends View {
  folder_id?: string;
}

export interface CreateViewResponse {
  id: string;
  view_url: string;
}

export interface PatchViewRequest {
  title?: string;
  query?: string;
  graph?: Graph;
  position?: number;
  folder_id?: string;
}

export interface PatchViewFolderRequest {
  name?: string;
}

export interface ExperimentListItem {
  id: string;
  created_at: string;
  updated_at?: string;
  author_name: string;
  title: string;
  description: string;
  result?: string;
  agent_id: string;
  metadata?: Record<string, unknown>;
}

export interface ExperimentListResponse {
  items: ExperimentListItem[];
  total: number;
  next_page_token?: string;
  previous_page_token?: string;
}

export interface AnnotationListResponse {
  items: Annotation[];
  total: number;
  next_page_token?: string;
  previous_page_token?: string;
}

export interface ViewListResponse {
  items: ViewFolder[];
  total: number;
  next_page_token?: string;
  previous_page_token?: string;
}

// API Keys
export interface APIKey {
  id: string;
  name: string;
  partial_key: string;
  created_at: string;
  last_used_at?: string;
  created_by: string;
}

export interface CompleteAPIKey extends APIKey {
  key: string;
}

export interface CreateAPIKeyRequest {
  name: string;
  created_by?: string;
}

export interface APIKeyListResponse {
  items: APIKey[];
  total: number;
  next_page_token?: string;
  previous_page_token?: string;
}

// Deployments
export interface Deployment {
  id: string;
  agent_id: string;
  version: Version;
  created_at: string;
  created_by: string;
  updated_at?: string;
  metadata?: Record<string, unknown>;
  url: string;
}

export interface DeploymentCreate {
  id: string;
  agent_id: string;
  version: Version;
  created_by: string;
  metadata?: Record<string, unknown>;
}

export interface DeploymentUpdate {
  version?: Version;
  metadata?: Record<string, unknown>;
}

export interface DeploymentListResponse {
  items: Deployment[];
  total: number;
  next_page_token?: string;
  previous_page_token?: string;
}

// Models
export interface SupportsModality {
  image: boolean;
  audio: boolean;
  pdf: boolean;
  text: boolean;
}

export interface ModelSupports {
  input: SupportsModality;
  output: SupportsModality;
  parallel_tool_calls: boolean;
  tools: boolean;
  top_p: boolean;
  temperature: boolean;
}

export interface ModelReasoning {
  can_be_disabled: boolean;
  low_effort_reasoning_budget: number;
  medium_effort_reasoning_budget: number;
  high_effort_reasoning_budget: number;
  min_reasoning_budget: number;
  max_reasoning_budget: number;
}

export interface ModelPricing {
  input_token_usd: number;
  output_token_usd: number;
}

export interface ModelContextWindow {
  max_tokens: number;
  max_output_tokens: number;
}

export interface Model {
  id: string;
  display_name: string;
  icon_url: string;
  supports: ModelSupports;
  pricing: ModelPricing;
  release_date: string;
  reasoning?: ModelReasoning;
  context_window: ModelContextWindow;
  speed_index: number;
}
