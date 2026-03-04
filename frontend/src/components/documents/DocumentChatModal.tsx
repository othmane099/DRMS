'use client';

import { useState, useEffect, useRef } from 'react';
import { Modal } from '@/components/ui';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface DocumentChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentName: string;
  versionNumber?: number;
  onSend: (message: string, signal: AbortSignal) => Promise<{ message: string }>;
  onLoadHistory?: () => Promise<{ messages: ChatMessage[] }>;
}

export function DocumentChatModal({
  isOpen,
  onClose,
  documentName,
  versionNumber,
  onSend,
  onLoadHistory,
}: DocumentChatModalProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    if (!onLoadHistory) return;
    setHistoryLoading(true);
    onLoadHistory()
      .then((data) => setMessages(data.messages))
      .catch(() => {/* silently ignore — history just won't be pre-loaded */})
      .finally(() => setHistoryLoading(false));
  }, [isOpen]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleClose = () => {
    abortRef.current?.abort();
    setMessages([]);
    setInput('');
    setError(null);
    onClose();
  };

  const handleStop = () => {
    abortRef.current?.abort();
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const controller = new AbortController();
    abortRef.current = controller;

    setInput('');
    setError(null);
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setLoading(true);
    try {
      const response = await onSend(text, controller.signal);
      setMessages((prev) => [...prev, { role: 'assistant', content: response.message }]);
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        // user stopped — remove the pending user message
        setMessages((prev) => prev.slice(0, -1));
      } else {
        setError('Failed to get a response. Please try again.');
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  };

  const title =
    versionNumber != null
      ? `Chat — ${documentName} · v${versionNumber}`
      : `Chat — ${documentName}`;

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={title} size="xl">
      <div className="flex flex-col" style={{ height: '420px' }}>
        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-3 pr-1 min-h-0">
          {historyLoading && (
            <p className="text-center text-sm text-gray-400 pt-16">Loading history…</p>
          )}
          {!historyLoading && messages.length === 0 && !loading && (
            <p className="text-center text-sm text-gray-400 pt-16">
              Ask anything about this document.
            </p>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] px-3 py-2 rounded-lg text-sm whitespace-pre-wrap leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-gray-900 text-white rounded-br-none'
                    : 'bg-gray-100 text-gray-800 rounded-bl-none'
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 text-gray-500 px-3 py-2 rounded-lg rounded-bl-none text-sm flex items-center gap-2">
                <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v8H4z"
                  />
                </svg>
                Thinking…
              </div>
            </div>
          )}
          {error && (
            <p className="text-xs text-center text-red-500 mt-2">{error}</p>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t mt-3 pt-3 flex gap-2 flex-shrink-0">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !loading) handleSend();
            }}
            placeholder="Ask a question about this document…"
            disabled={loading}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          {loading ? (
            <button
              onClick={handleStop}
              className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700"
            >
              Stop
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="px-4 py-2 bg-black text-white text-sm font-medium rounded-md hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}
