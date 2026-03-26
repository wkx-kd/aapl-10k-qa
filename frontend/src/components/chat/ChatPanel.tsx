import { useRef, useEffect } from 'react';
import type { Message, Filters } from '../../types';
import MessageBubble from './MessageBubble';
import ChatInput from './ChatInput';

interface ChatPanelProps {
  messages: Message[];
  isStreaming: boolean;
  filters: Filters;
  onSendMessage: (query: string, filters: Filters) => void;
  onClear: () => void;
}

export default function ChatPanel({
  messages,
  isStreaming,
  filters,
  onSendMessage,
  onClear,
}: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-slate-400">
            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-4">
              <span className="text-2xl">📊</span>
            </div>
            <p className="text-lg font-medium text-slate-500 mb-2">AAPL 10-K Intelligence</p>
            <p className="text-sm text-center max-w-md">
              Ask questions about Apple's 10-K filings (2020-2025).
              Try financial queries, risk analysis, or cross-year comparisons.
            </p>
            <div className="mt-4 grid grid-cols-2 gap-2 max-w-lg">
              {[
                "What was Apple's revenue in 2025?",
                "What are the main risk factors?",
                "Compare net income from 2020 to 2025",
                "What products does Apple sell?",
              ].map((q, i) => (
                <button
                  key={i}
                  onClick={() => onSendMessage(q, filters)}
                  className="text-xs text-left text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg px-3 py-2 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput
        onSend={(query) => onSendMessage(query, filters)}
        disabled={isStreaming}
        onClear={onClear}
        hasMessages={messages.length > 0}
      />
    </div>
  );
}
