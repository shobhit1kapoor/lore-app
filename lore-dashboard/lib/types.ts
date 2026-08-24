export type TelemetryEvent = {
  event_type: string;
  trace_id: string;
  event_id: string;
  timestamp: string;
  agent_name?: string | null;
  source?: string | null;
  destination?: string | null;
  resource?: string | null;
  tool_name?: string | null;
  data_categories?: string[];
  protection_action?: string | null;
  policy_result?: string | null;
  risk_score?: number | null;
  latency_ms?: number | null;
  metadata?: Record<string, unknown>;
  previous_hash?: string | null;
  event_hash?: string | null;
};

export type TraceSummary = {
  trace_id: string;
  event_count: number;
  started_at?: string;
  last_event_at?: string;
  agents: string[];
  event_types: string[];
  data_categories: string[];
  blocked: boolean;
  max_risk_score: number;
};

export type Overview = {
  event_count: number;
  trace_count: number;
  blocked_count: number;
  tokenized_count: number;
  masked_count: number;
  sensitive_discovery_count: number;
  event_counts: Record<string, number>;
  category_counts: Record<string, number>;
  recent_traces: TraceSummary[];
  evidence_chain: {valid: boolean; checked_events: number; broken_event_id?: string | null};
};

export type Readiness = {
  ready: boolean;
  protection_provider: string;
  privacy_gateway_isolated: boolean;
  fail_closed: boolean;
  model_provider: string;
  credentials_exposed_to_api: boolean;
};

export type AttackScenario = {
  id: string;
  title: string;
  category: string;
  boundary: string;
  prompt: string;
};

export type AIReviewResponse = {
  trace_id: string;
  response: string;
  model_provider: string;
  protection_provider: string;
  provider_payload_status: string;
};

export type ProtectionResponse = {
  trace_id: string;
  text: string;
  categories: string[];
  findings: Array<{category: string; start: number; end: number; action: string; confidence: number}>;
  tokenized_count: number;
  masked_count: number;
  blocked: boolean;
  risk_score: number;
  policy_result: string;
  reason?: string | null;
  provider?: string;
  fingerprint?: string | null;
  entity_counts?: Record<string, number>;
  scenario_id?: string | null;
  blocked_boundary?: string | null;
};

export type MemoryRecord = {
  id: string;
  source_mr_number: number;
  source_mr_title: string;
  date: string;
  governs_files: string[];
  decision: string;
  rejected: string;
  reason: string;
  future_implication: string;
  decided_by: string[];
  confidence: number;
  status: string;
};
