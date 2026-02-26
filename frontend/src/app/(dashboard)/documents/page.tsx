'use client';

import { AIDocumentSearch, DocumentsList } from '@/components/documents';
import { api } from '@/lib/api';

export default function DocumentsPage() {
  return (
    <div className="space-y-6">
      <AIDocumentSearch
        onSearch={(query) => api.searchDocuments(query)}
        placeholder="e.g. list all contracts assigned to John created in 2024"
      />

      <DocumentsList
        title="Documents"
        description="Manage your digital records and documents"
        basePath="/documents"
        permissions={{
          list: 'documents.list',
          create: 'documents.create',
          edit: 'documents.update',
          delete: 'documents.delete',
          share: 'documents.share',
          archive: 'documents.archive',
        }}
        apiFunctions={{
          getDocuments: (filters) => api.getDocuments(filters),
          deleteDocument: (id) => api.deleteDocument(id),
          archiveDocument: (id) => api.archiveDocument(id),
          updateDocument: (id, data) => api.updateDocument(id, data),
          generateShareLink: (id, data) => api.generateShareLink(id, data),
        }}
      />
    </div>
  );
}