import { useState, useEffect } from 'react';
import type { GraphEntities } from '../../types';
import { fetchGraphEntities } from '../../services/api';
import { Loader2, Box, MapPin, AlertTriangle, Users } from 'lucide-react';

export default function GraphViewer() {
  const [entities, setEntities] = useState<GraphEntities | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGraphEntities()
      .then(data => {
        setEntities(data);
        setError(null);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400">
        <Loader2 size={24} className="animate-spin mr-2" />
        Loading knowledge graph...
      </div>
    );
  }

  if (error || !entities) {
    return (
      <div className="flex items-center justify-center h-full text-red-500">
        Failed to load graph: {error}
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      {/* Entity Counts */}
      <div className="grid grid-cols-3 gap-4">
        {Object.entries(entities.entity_counts || {}).map(([label, count]) => (
          <div key={label} className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <p className="text-xs text-slate-500 font-medium">{label}</p>
            <p className="text-2xl font-bold text-slate-800">{count}</p>
          </div>
        ))}
      </div>

      {/* Products */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
          <Box size={16} className="text-blue-500" /> Products
        </h3>
        <div className="grid grid-cols-2 gap-2">
          {entities.products?.map(p => (
            <div key={p.name} className="flex items-center gap-2 bg-blue-50 rounded-lg px-3 py-2">
              <span className="text-sm font-medium text-blue-700">{p.name}</span>
              <span className="text-xs text-blue-500">{p.category}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Segments */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
          <MapPin size={16} className="text-green-500" /> Geographic Segments
        </h3>
        <div className="flex flex-wrap gap-2">
          {entities.segments?.map(s => (
            <span key={s.name} className="bg-green-50 text-green-700 text-sm rounded-full px-3 py-1">
              {s.name}
            </span>
          ))}
        </div>
      </div>

      {/* Executives */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
          <Users size={16} className="text-indigo-500" /> Leadership
        </h3>
        <div className="space-y-2">
          {entities.executives?.map(e => (
            <div key={e.name} className="flex items-center justify-between bg-indigo-50 rounded-lg px-3 py-2">
              <span className="text-sm font-medium text-indigo-700">{e.name}</span>
              <span className="text-xs text-indigo-500">{e.role}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Risk Categories */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
          <AlertTriangle size={16} className="text-amber-500" /> Risk Categories
        </h3>
        <div className="space-y-2">
          {entities.risk_categories?.map(r => (
            <div key={r.name} className="bg-amber-50 rounded-lg px-3 py-2">
              <p className="text-sm font-medium text-amber-700">{r.name}</p>
              <p className="text-xs text-amber-600 mt-0.5">{r.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
