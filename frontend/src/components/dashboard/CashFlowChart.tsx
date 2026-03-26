import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import type { FinancialSummary } from '../../types';

interface Props {
  data: FinancialSummary[];
}

export default function CashFlowChart({ data }: Props) {
  const chartData = data.map(d => ({
    year: d.year,
    'Current Ratio': d.current_ratio ? +d.current_ratio.toFixed(2) : null,
    'D/E Ratio': d.debt_to_equity ? +d.debt_to_equity.toFixed(2) : null,
  }));

  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="year" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="Current Ratio" stroke="#06b6d4" strokeWidth={2} dot={{ r: 4 }} />
        <Line type="monotone" dataKey="D/E Ratio" stroke="#f43f5e" strokeWidth={2} dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
