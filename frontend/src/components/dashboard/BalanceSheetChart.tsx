import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import type { FinancialSummary } from '../../types';

interface Props {
  data: FinancialSummary[];
}

export default function BalanceSheetChart({ data }: Props) {
  const chartData = data.map(d => ({
    year: d.year,
    'Total Assets': d.total_assets ? +(d.total_assets / 1e9).toFixed(1) : 0,
    Cash: d.cash_and_equivalents ? +(d.cash_and_equivalents / 1e9).toFixed(1) : 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="year" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: any) => `$${v}B`} />
        <Tooltip formatter={(v: any) => `$${v}B`} />
        <Legend />
        <Bar dataKey="Total Assets" fill="#6366f1" radius={[4, 4, 0, 0]} />
        <Bar dataKey="Cash" fill="#06b6d4" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
