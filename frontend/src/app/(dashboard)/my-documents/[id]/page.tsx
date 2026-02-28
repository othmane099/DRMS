'use client';

import { useParams } from 'next/navigation';
import { DocumentDetail } from '@/components/documents';
import { api } from '@/lib/api';

export default function MyDocumentDetailPage() {
  const params = useParams();
  const documentId = params.id as string;

  return (
    <DocumentDetail
      documentId={documentId}
      backPath="/my-documents"
      permissions={{
        view: 'documents.list_my',
        edit: 'documents.update_my',
        viewVersion: 'documents.view_version_my',
        createVersion: 'documents.create_version_my',
        viewComments: 'comments.list_my',
        createComment: 'comments.create_my',
        share: 'documents.share_my',
        viewShared: 'documents.view_my',
        deleteShare: 'documents.share_my',
        viewReminders: 'reminders.list_my',
        createReminder: 'reminders.create_my',
        viewReminderDetail: 'reminders.view_my',
        updateReminder: 'reminders.update_my',
        deleteReminder: 'reminders.delete_my',
        chat: 'documents.chat_my',
      }}
      apiFunctions={{
        getDocument: (id) => api.getMyDocument(id),
        getVersions: (id) => api.getMyDocumentVersions(id),
        getComments: (id) => api.getMyDocumentComments(id),
        getSharedUsers: (id) => api.getMySharedUsers(id),
        getReminders: (id) => api.getMyDocumentReminders(id),
        getReminder: (id) => api.getMyReminder(id),
        createVersion: (id, file) => api.createMyDocumentVersion(id, file),
        createComment: (id, data) => api.createMyDocumentComment(id, data),
        shareDocument: (id, data) => api.shareMyDocument(id, data),
        deleteShare: (docId, shareId) => api.deleteMyShare(docId, shareId),
        createReminder: (id, data) => api.createMyDocumentReminder(id, data),
        updateReminder: (id, data) => api.updateMyReminder(id, data),
        deleteReminder: (id) => api.deleteMyReminder(id),
        downloadDocument: (id) => api.downloadMyDocument(id),
        downloadVersion: (docId, versionId) => api.downloadMyDocumentVersion(docId, versionId),
        updateDocument: (id, data) => api.updateMyDocument(id, data),
        chatWithVersion: (docId, versionId, msg) =>
          api.chatMyDocumentVersion(docId, versionId, msg),
      }}
      previewUrlSuffix="/me"
    />
  );
}