import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../../types';
import SourceCitation from './SourceCitation';
import { User, Bot, Database, BookOpen, Share2, Shuffle, Loader2 } from 'lucide-react';

interface MessageBubbleProps {
  message: Message;
}

const intentConfig: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  quantitative: { label: 'SQL', icon: <Database size={12} />, color: 'bg-emerald-100 text-emerald-700' },
  narrative: { label: 'RAG', icon: <BookOpen size={12} />, color: 'bg-blue-100 text-blue-700' },
  relationship: { label: 'Graph', icon: <Share2 size={12} />, color: 'bg-purple-100 text-purple-700' },
  hybrid: { label: 'Hybrid', icon: <Shuffle size={12} />, color: 'bg-amber-100 text-amber-700' },
};

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const intent = message.intent ? intentConfig[message.intent] : null;

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shrink-0">
          <Bot size={16} className="text-white" />
        </div>
      )}

      <div className={`max-w-[75%] ${isUser ? 'order-first' : ''}`}>
        {/* Intent badge */}
        {intent && (
          <div className="mb-1">
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${intent.color}`}>
              {intent.icon} {intent.label}
            </span>
          </div>
        )}

        {/* Message content */}
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-blue-600 text-white rounded-tr-md'
              : 'bg-white border border-slate-200 text-slate-700 rounded-tl-md shadow-sm'
          }`}
        >
          {isUser ? (
            <p className="text-sm">{message.content}</p>
          ) : (
            <div className="text-sm markdown-content">
              {message.content ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
              ) : message.isStreaming ? (
                <div className="flex items-center gap-2 text-slate-400">
                  <Loader2 size={14} className="animate-spin" />
                  <span>Thinking...</span>
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <SourceCitation sources={message.sources} />
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-slate-200 flex items-center justify-center shrink-0">
          <User size={16} className="text-slate-600" />
        </div>
      )}
    </div>
  );
}
