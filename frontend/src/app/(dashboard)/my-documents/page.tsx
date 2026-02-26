'use client';

import { useState } from 'react';
import { DocumentsList } from '@/components/documents';
import { api } from '@/lib/api';

export default function MyDocumentsPage() {
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
      const response = await api.searchMyDocuments(query);
      setResult(response.message);
    } catch {
      setError('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">AI Document Search</h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !loading && handleSearch()}
            placeholder="e.g. show my documents in the Financial category"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Searching...
              </span>
            ) : 'Search'}
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

      <DocumentsList
        title="My Documents"
        description="View and manage documents created by you"
        basePath="/my-documents"
        permissions={{
          list: 'documents.list_my',
          create: 'documents.create_my',
          edit: 'documents.update_my',
          delete: 'documents.delete_my',
          share: 'documents.share_my',
          archive: 'documents.archive_my',
        }}
        apiFunctions={{
          getDocuments: (filters) => api.getMyDocuments(filters),
          deleteDocument: (id) => api.deleteMyDocument(id),
          archiveDocument: (id) => api.archiveMyDocument(id),
          updateDocument: (id, data) => api.updateMyDocument(id, data),
          generateShareLink: (id, data) => api.generateMyShareLink(id, data),
        }}
      />
    </div>
  );
}