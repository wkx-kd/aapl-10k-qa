import { TrendingUp, TrendingDown } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string;
  change: number | null;
  year: number;
}

export default function MetricCard({ title, value, change, year }: MetricCardProps) {
  const isPositive = change != null && change > 0;
  const isNegative = change != null && change < 0;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
      <p className="text-xs text-slate-500 font-medium">{title} (FY{year})</p>
      <p className="text-2xl font-bold text-slate-800 mt-1">{value}</p>
      {change != null && (
        <div className={`flex items-center gap-1 mt-1 text-xs font-medium ${
          isPositive ? 'text-emerald-600' : isNegative ? 'text-red-500' : 'text-slate-500'
        }`}>
          {isPositive ? <TrendingUp size={12} /> : isNegative ? <TrendingDown size={12} /> : null}
          {isPositive ? '+' : ''}{(change * 100).toFixed(1)}% YoY
        </div>
      )}
    </div>
  );
}
