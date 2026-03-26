import type { Filters, FinancialSummary, GraphEntities } from '../types';

const API_BASE = '/api';

export async function fetchSections(): Promise<{ years: number[]; sections: any[] }> {
  const res = await fetch(`${API_BASE}/sections`);
  return res.json();
}

export async function fetchFinancialMetrics(years?: number[]) {
  const params = years ? `?years=${years.join(',')}` : '';
  const res = await fetch(`${API_BASE}/financial/metrics${params}`);
  return res.json();
}

export async function fetchFinancialSummary(): Promise<{ summary: FinancialSummary[] }> {
  const res = await fetch(`${API_BASE}/financial/summary`);
  return res.json();
}

export async function fetchFinancialCompare(metric: string, years?: number[]) {
  const params = new URLSearchParams({ metric });
  if (years) params.set('years', years.join(','));
  const res = await fetch(`${API_BASE}/financial/compare?${params}`);
  return res.json();
}

export async function fetchGraphEntities(): Promise<GraphEntities> {
  const res = await fetch(`${API_BASE}/graph/entities`);
  return res.json();
}

export async function fetchGraphQuery(q: string) {
  const res = await fetch(`${API_BASE}/graph/query?q=${encodeURIComponent(q)}`);
  return res.json();
}

export async function* streamChat(
  query: string,
  filters: Filters,
  history: Array<{ role: string; content: string }>,
  topK: number = 5,
): AsyncGenerator<any> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      filters: {
        years: filters.years.length > 0 ? filters.years : undefined,
        sections: filters.sections.length > 0 ? filters.sections : undefined,
      },
      history,
      top_k: topK,
      stream: true,
    }),
  });

  if (!res.ok) {
    throw new Error(`Chat API error: ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          yield data;
        } catch {
          // Skip malformed JSON
        }
      }
    }
  }
}
