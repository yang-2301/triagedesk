declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<{}, {}, any>;
  export default component;
}

export interface Ticket {
  id: string;
  title: string;
  description: string;
  status: "open" | "in_progress" | "resolved" | "closed";
  priority: "urgent" | "high" | "normal" | "low";
  category: "billing" | "bug" | "feature" | "account" | "general";
  triage_source: string;
  triage_confidence: string | null;
  suggested_reply: string | null;
  created_by: string;
  assigned_to: string | null;
  created_at: string;
  first_response_at: string | null;
  resolved_at: string | null;
}

export interface Comment {
  id: string;
  author_id: string;
  body: string;
  is_internal: boolean;
  created_at: string;
}

export interface Dashboard {
  total: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  by_category: Record<string, number>;
  sla_breach_count: number;
  sla_breach_rate: number;
  breached_tickets: { id: string; title: string; priority: string; created_at: string }[];
  median_first_response_hours: number | null;
  trend: { date: string; created: number; resolved: number }[];
}
