'use client';

import { useState } from 'react';

interface Props {
  onSearch: (query: string) => Promise<{ message: string }>;
  placeholder?: string;
}

export function AIDocumentSearch({ onSearch, placeholder }: Props) {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const response = await onSearch(query);
      setResult(response.message);
    } catch {
      setError('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">AI Filter</h3>
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !loading && handleSearch()}
          placeholder={placeholder ?? 'e.g. list all contracts assigned to John created in 2024'}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="px-4 py-2 bg-black text-white text-sm font-medium rounded-md hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Searching...
            </span>
          ) : 'Filter'}
        </button>
      </div>

      {result && (
        <div className="mt-3 p-3 bg-blue-50 border border-blue-100 rounded-md text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
          {result}
        </div>
      )}

      {error && (
        <div className="mt-3 p-3 bg-red-50 border border-red-100 rounded-md text-sm text-red-600">
          {error}
        </div>
      )}
    </div>
  );
}