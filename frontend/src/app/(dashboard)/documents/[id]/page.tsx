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
        viewMy: 'documents.list_my',
        edit: 'documents.update',
        editMy: 'documents.update_my',
        viewVersion: 'documents.view_version',
        viewVersionMy: 'documents.view_version_my',
        createVersion: 'documents.create_version',
        createVersionMy: 'documents.create_version_my',
        viewComments: 'comments.list',
        viewCommentsMy: 'comments.list_my',
        createComment: 'comments.create',
        createCommentMy: 'comments.create_my',
        share: 'documents.share',
        shareMy: 'documents.share_my',
        viewShared: 'documents.view',
        viewSharedMy: 'documents.view_my',
        deleteShare: 'documents.delete_share',
        deleteShareMy: 'documents.delete_share_my',
        viewReminders: 'reminders.list',
        viewRemindersMy: 'reminders.list_my',
        createReminder: 'reminders.create',
        createReminderMy: 'reminders.create_my',
        viewReminderDetail: 'reminders.view',
        viewReminderDetailMy: 'reminders.view_my',
        updateReminder: 'reminders.update',
        updateReminderMy: 'reminders.update_my',
        deleteReminder: 'reminders.delete',
        deleteReminderMy: 'reminders.delete_my',
        preview: 'documents.preview',
        previewMy: 'documents.preview_my',
        previewVersion: 'documents.preview_version',
        previewVersionMy: 'documents.preview_version_my',
        download: 'documents.download',
        downloadMy: 'documents.download_my',
        downloadVersion: 'documents.download_version',
        downloadVersionMy: 'documents.download_version_my',
        chat: 'documents.chat',
        chatMy: 'documents.chat_my',
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
        chatWithVersion: (docId, versionId, msg) =>
          api.chatWithDocumentVersion(docId, versionId, msg),
        getChatHistory: (docId, versionId) =>
          api.getChatHistory(docId, versionId),
      }}
      previewUrlSuffix=""
    />
  );
}