export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  sources?: Source[];
  isStreaming?: boolean;
}

export interface Source {
  type: 'vector' | 'sql' | 'graph';
  chunk_id?: string;
  year?: number;
  section_title?: string;
  section_category?: string;
  score?: number;
  text?: string;
  query?: string;
  results?: any;
}

export interface Filters {
  years: number[];
  sections: string[];
}

export interface FinancialMetrics {
  [year: number]: {
    year: number;
    income_statement: Record<string, number | null>;
    balance_sheet: Record<string, number | null>;
    cash_flow: Record<string, number | null>;
    derived_metrics: Record<string, number | null>;
  };
}

export interface FinancialSummary {
  year: number;
  revenue: number;
  net_income: number;
  eps_diluted: number;
  gross_margin: number;
  operating_margin: number;
  net_margin: number;
  free_cash_flow: number;
  revenue_yoy_growth: number;
  total_assets: number;
  cash_and_equivalents: number;
  current_ratio: number;
  debt_to_equity: number;
}

export interface GraphEntities {
  entity_counts: Record<string, number>;
  products: Array<{ name: string; category: string }>;
  segments: Array<{ name: string }>;
  risk_categories: Array<{ name: string; description: string }>;
  executives: Array<{ name: string; role: string }>;
}

export interface SectionInfo {
  section_id: number;
  section_title: string;
  section_category: string;
}

export type TabType = 'chat' | 'dashboard' | 'graph';
