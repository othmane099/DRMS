'use client';

import { AIDocumentSearch, DocumentsList } from '@/components/documents';
import { api } from '@/lib/api';

export default function MyDocumentsPage() {
  return (
    <div className="space-y-6">
      <AIDocumentSearch
        onSearch={(query) => api.searchMyDocuments(query)}
        placeholder="e.g. show my documents in the Financial category"
      />

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