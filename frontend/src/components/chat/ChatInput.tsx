import { useState, useRef, useEffect } from 'react';
import { Send, Trash2 } from 'lucide-react';

interface ChatInputProps {
  onSend: (query: string) => void;
  disabled: boolean;
  onClear: () => void;
  hasMessages: boolean;
}

export default function ChatInput({ onSend, disabled, onClear, hasMessages }: ChatInputProps) {
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, [disabled]);

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-slate-200 bg-white p-4">
      <div className="flex items-end gap-2">
        {hasMessages && (
          <button
            onClick={onClear}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            title="Clear chat"
          >
            <Trash2 size={18} />
          </button>
        )}
        <div className="flex-1 relative">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about Apple's 10-K filings..."
            disabled={disabled}
            rows={1}
            className="w-full resize-none rounded-xl border border-slate-300 px-4 py-2.5 text-sm text-slate-700 placeholder-slate-400 focus:border-blue-400 focus:ring-1 focus:ring-blue-400 focus:outline-none disabled:opacity-50 disabled:bg-slate-50"
          />
        </div>
        <button
          onClick={handleSubmit}
          disabled={disabled || !input.trim()}
          className="p-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
