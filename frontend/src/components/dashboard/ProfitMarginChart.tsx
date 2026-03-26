import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import type { FinancialSummary } from '../../types';

interface Props {
  data: FinancialSummary[];
}

export default function ProfitMarginChart({ data }: Props) {
  const chartData = data.map(d => ({
    year: d.year,
    'Gross Margin': d.gross_margin ? +(d.gross_margin * 100).toFixed(1) : null,
    'Operating Margin': d.operating_margin ? +(d.operating_margin * 100).toFixed(1) : null,
    'Net Margin': d.net_margin ? +(d.net_margin * 100).toFixed(1) : null,
  }));

  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="year" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: any) => `${v}%`} />
        <Tooltip formatter={(v: any) => `${v}%`} />
        <Legend />
        <Line type="monotone" dataKey="Gross Margin" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 4 }} />
        <Line type="monotone" dataKey="Operating Margin" stroke="#f59e0b" strokeWidth={2} dot={{ r: 4 }} />
        <Line type="monotone" dataKey="Net Margin" stroke="#ef4444" strokeWidth={2} dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
