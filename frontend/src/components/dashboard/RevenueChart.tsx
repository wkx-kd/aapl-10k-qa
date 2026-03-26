import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import type { FinancialSummary } from '../../types';

interface Props {
  data: FinancialSummary[];
}

export default function RevenueChart({ data }: Props) {
  const chartData = data.map(d => ({
    year: d.year,
    Revenue: d.revenue ? +(d.revenue / 1e9).toFixed(1) : 0,
    'Net Income': d.net_income ? +(d.net_income / 1e9).toFixed(1) : 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="year" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: any) => `$${v}B`} />
        <Tooltip formatter={(v: any) => `$${v}B`} />
        <Legend />
        <Line type="monotone" dataKey="Revenue" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
        <Line type="monotone" dataKey="Net Income" stroke="#10b981" strokeWidth={2} dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
