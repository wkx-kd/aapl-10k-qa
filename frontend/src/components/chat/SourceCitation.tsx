import { useState } from 'react';
import type { Source } from '../../types';
import { ChevronDown, ChevronUp, Database, BookOpen, Share2 } from 'lucide-react';

interface SourceCitationProps {
  sources: Source[];
}

const sourceIcons: Record<string, React.ReactNode> = {
  sql: <Database size={12} className="text-emerald-600" />,
  vector: <BookOpen size={12} className="text-blue-600" />,
  graph: <Share2 size={12} className="text-purple-600" />,
};

const sourceColors: Record<string, string> = {
  sql: 'border-emerald-200 bg-emerald-50',
  vector: 'border-blue-200 bg-blue-50',
  graph: 'border-purple-200 bg-purple-50',
};

export default function SourceCitation({ sources }: SourceCitationProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 transition-colors"
      >
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        {sources.length} source{sources.length !== 1 ? 's' : ''}
      </button>

      {expanded && (
        <div className="mt-1.5 space-y-1.5">
          {sources.map((source, i) => (
            <div
              key={i}
              className={`rounded-lg border p-2 text-xs ${sourceColors[source.type] || 'border-slate-200 bg-slate-50'}`}
            >
              <div className="flex items-center gap-1.5 mb-1">
                {sourceIcons[source.type]}
                <span className="font-medium text-slate-700 uppercase">{source.type}</span>
                {source.year && (
                  <span className="text-slate-500">| {source.year}</span>
                )}
                {source.section_title && (
                  <span className="text-slate-500 truncate">| {source.section_title}</span>
                )}
                {source.score != null && (
                  <span className="ml-auto text-slate-400">
                    {(source.score * 100).toFixed(0)}%
                  </span>
                )}
              </div>
              {source.text && (
                <p className="text-slate-600 line-clamp-3">{source.text}</p>
              )}
              {source.query && (
                <code className="block text-slate-600 bg-white/50 rounded px-1.5 py-1 mt-1 break-all">
                  {source.query}
                </code>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
