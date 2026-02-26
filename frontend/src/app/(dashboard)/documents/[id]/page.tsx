'use client';

import { useParams } from 'next/navigation';
import { DocumentDetail } from '@/components/documents';
import { api } from '@/lib/api';

export default function DocumentDetailPage() {
  const params = useParams();
  const documentId = params.id as string;

  return (
    <DocumentDetail
      documentId={documentId}
      backPath="/documents"
      permissions={{
        view: 'documents.list',
        edit: 'documents.update',
        viewVersion: 'documents.view_version',
        createVersion: 'documents.create_version',
        viewComments: 'comments.list',
        createComment: 'comments.create',
        share: 'documents.share',
        viewShared: 'documents.view',
        deleteShare: 'documents.delete_share',
        viewReminders: 'reminders.list',
        createReminder: 'reminders.create',
        viewReminderDetail: 'reminders.view',
        updateReminder: 'reminders.update',
        deleteReminder: 'reminders.delete',
      }}
      apiFunctions={{
        getDocument: (id) => api.getDocument(id),
        getVersions: (id) => api.getDocumentVersions(id),
        getComments: (id) => api.getDocumentComments(id),
        getSharedUsers: (id) => api.getSharedUsers(id),
        getReminders: (id) => api.getDocumentReminders(id),
        getReminder: (id) => api.getReminder(id),
        createVersion: (id, file) => api.createDocumentVersion(id, file),
        createComment: (id, data) => api.createDocumentComment(id, data),
        shareDocument: (id, data) => api.shareDocument(id, data),
        deleteShare: (docId, shareId) => api.deleteShare(docId, shareId),
        createReminder: (id, data) => api.createDocumentReminder(id, data),
        updateReminder: (id, data) => api.updateReminder(id, data),
        deleteReminder: (id) => api.deleteReminder(id),
        downloadDocument: (id) => api.downloadDocument(id),
        downloadVersion: (docId, versionId) => api.downloadDocumentVersion(docId, versionId),
        updateDocument: (id, data) => api.updateDocument(id, data),
      }}
      previewUrlSuffix=""
    />
  );
}