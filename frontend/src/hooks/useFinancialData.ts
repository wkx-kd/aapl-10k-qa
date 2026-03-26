import { useState, useEffect } from 'react';
import type { FinancialSummary } from '../types';
import { fetchFinancialSummary } from '../services/api';

export function useFinancialData() {
  const [summary, setSummary] = useState<FinancialSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        const data = await fetchFinancialSummary();
        if (!cancelled) {
          setSummary(data.summary || []);
          setError(null);
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err.message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  return { summary, loading, error };
}
