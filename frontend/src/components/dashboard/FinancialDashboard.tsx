import { useFinancialData } from '../../hooks/useFinancialData';
import MetricCard from './MetricCard';
import RevenueChart from './RevenueChart';
import ProfitMarginChart from './ProfitMarginChart';
import BalanceSheetChart from './BalanceSheetChart';
import CashFlowChart from './CashFlowChart';
import { Loader2, AlertCircle } from 'lucide-react';

export default function FinancialDashboard() {
  const { summary, loading, error } = useFinancialData();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400">
        <Loader2 size={24} className="animate-spin mr-2" />
        Loading financial data...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-red-500">
        <AlertCircle size={20} className="mr-2" />
        Failed to load financial data: {error}
      </div>
    );
  }

  const latest = summary[summary.length - 1];
  if (!latest) return null;

  const formatB = (v: number | null) => v ? `$${(v / 1e9).toFixed(1)}B` : 'N/A';
  const prev = summary.length > 1 ? summary[summary.length - 2] : null;

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard
          title="Revenue"
          value={formatB(latest.revenue)}
          change={latest.revenue_yoy_growth}
          year={latest.year}
        />
        <MetricCard
          title="Net Income"
          value={formatB(latest.net_income)}
          change={prev ? (latest.net_income - prev.net_income) / Math.abs(prev.net_income) : null}
          year={latest.year}
        />
        <MetricCard
          title="EPS (Diluted)"
          value={latest.eps_diluted ? `$${latest.eps_diluted.toFixed(2)}` : 'N/A'}
          change={prev?.eps_diluted ? (latest.eps_diluted - prev.eps_diluted) / prev.eps_diluted : null}
          year={latest.year}
        />
        <MetricCard
          title="Free Cash Flow"
          value={formatB(latest.free_cash_flow)}
          change={prev?.free_cash_flow ? (latest.free_cash_flow - prev.free_cash_flow) / Math.abs(prev.free_cash_flow) : null}
          year={latest.year}
        />
      </div>

      {/* Charts - 2 columns */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Revenue Trend</h3>
          <RevenueChart data={summary} />
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Profit Margins</h3>
          <ProfitMarginChart data={summary} />
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Balance Sheet</h3>
          <BalanceSheetChart data={summary} />
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Key Ratios</h3>
          <CashFlowChart data={summary} />
        </div>
      </div>
    </div>
  );
}
