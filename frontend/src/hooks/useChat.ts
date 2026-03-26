import { useState, useCallback } from 'react';
import type { Message, Filters } from '../types';
import { streamChat } from '../services/api';

let messageIdCounter = 0;

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const sendMessage = useCallback(async (query: string, filters: Filters) => {
    if (isStreaming) return;

    const userMsg: Message = {
      id: `msg-${++messageIdCounter}`,
      role: 'user',
      content: query,
    };

    const assistantMsg: Message = {
      id: `msg-${++messageIdCounter}`,
      role: 'assistant',
      content: '',
      isStreaming: true,
    };

    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    const history = messages
      .filter(m => !m.isStreaming)
      .slice(-6)
      .map(m => ({ role: m.role, content: m.content }));

    try {
      for await (const event of streamChat(query, filters, history)) {
        switch (event.type) {
          case 'intent':
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantMsg.id ? { ...m, intent: event.intent } : m
              )
            );
            break;
          case 'sources':
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantMsg.id ? { ...m, sources: event.sources } : m
              )
            );
            break;
          case 'token':
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantMsg.id
                  ? { ...m, content: m.content + event.content }
                  : m
              )
            );
            break;
          case 'done':
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantMsg.id ? { ...m, isStreaming: false } : m
              )
            );
            break;
          case 'error':
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantMsg.id
                  ? { ...m, content: `Error: ${event.message}`, isStreaming: false }
                  : m
              )
            );
            break;
        }
      }
    } catch (err: any) {
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantMsg.id
            ? { ...m, content: `Error: ${err.message}`, isStreaming: false }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
    }
  }, [messages, isStreaming]);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return { messages, isStreaming, sendMessage, clearMessages };
}
