import type { Filters, SectionInfo } from '../../types';
import { Filter, X } from 'lucide-react';

interface FilterSidebarProps {
  filters: Filters;
  availableYears: number[];
  availableSections: SectionInfo[];
  onToggleYear: (year: number) => void;
  onToggleSection: (category: string) => void;
  onClear: () => void;
}

const SECTION_CATEGORIES = [
  { key: 'business', label: 'Business' },
  { key: 'risk', label: 'Risk Factors' },
  { key: 'mda', label: 'MD&A' },
  { key: 'financial', label: 'Financial' },
  { key: 'financial_table', label: 'Financial Tables' },
  { key: 'legal', label: 'Legal' },
  { key: 'governance', label: 'Governance' },
  { key: 'compensation', label: 'Compensation' },
];

export default function FilterSidebar({
  filters,
  availableYears,
  onToggleYear,
  onToggleSection,
  onClear,
}: FilterSidebarProps) {
  const hasFilters = filters.years.length > 0 || filters.sections.length > 0;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-sm font-semibold text-slate-700">
          <Filter size={14} />
          Filters
        </div>
        {hasFilters && (
          <button
            onClick={onClear}
            className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-0.5"
          >
            <X size={12} /> Clear
          </button>
        )}
      </div>

      {/* Year Filter */}
      <div>
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Fiscal Year
        </h3>
        <div className="space-y-1">
          {availableYears.map(year => (
            <label
              key={year}
              className="flex items-center gap-2 cursor-pointer hover:bg-slate-50 rounded px-1 py-0.5"
            >
              <input
                type="checkbox"
                checked={filters.years.includes(year)}
                onChange={() => onToggleYear(year)}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-slate-600">{year}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Section Filter */}
      <div>
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Section Type
        </h3>
        <div className="space-y-1">
          {SECTION_CATEGORIES.map(cat => (
            <label
              key={cat.key}
              className="flex items-center gap-2 cursor-pointer hover:bg-slate-50 rounded px-1 py-0.5"
            >
              <input
                type="checkbox"
                checked={filters.sections.includes(cat.key)}
                onChange={() => onToggleSection(cat.key)}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-slate-600">{cat.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Active filter summary */}
      {hasFilters && (
        <div className="bg-blue-50 rounded-lg p-2">
          <p className="text-xs text-blue-600 font-medium">
            Active: {filters.years.length > 0 ? `Years: ${filters.years.join(', ')}` : ''}
            {filters.years.length > 0 && filters.sections.length > 0 ? ' | ' : ''}
            {filters.sections.length > 0 ? `Sections: ${filters.sections.length}` : ''}
          </p>
        </div>
      )}
    </div>
  );
}
