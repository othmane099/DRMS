'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Card, CardHeader, LoadingOverlay, Badge, Toast, Tabs, Modal } from '@/components/ui';
import { DocumentModal } from '@/components/documents';
import { CanAccess } from '@/components/auth/CanAccess';
import { AccessDenied } from '@/components/auth/AccessDenied';
import { usePermissions } from '@/hooks/usePermissions';
import { useAuth } from '@/hooks/useAuth';
import { api } from '@/lib/api';
import {
  Document, ApiError, DocumentVersion, DocumentComment, SharedUser, User, DocumentReminder, VersionHistoryResponse,
  UserBasicId
} from '@/types';
import { formatDateTime } from '@/lib/utils';

interface DocumentDetailProps {
  documentId: string;
  backPath: string;
  permissions: {
    view: string;
    edit: string;
    viewVersion: string;
    createVersion: string;
    viewComments: string;
    createComment: string;
    share: string;
    viewShared: string;
    deleteShare: string;
    viewReminders: string;
    createReminder: string;
    viewReminderDetail: string;
    updateReminder: string;
    deleteReminder: string;
  };
  apiFunctions: {
    getDocument: (id: string) => Promise<Document>;
    getVersions: (id: string) => Promise<DocumentVersion[]>;
    getComments: (id: string) => Promise<DocumentComment[]>;
    getSharedUsers: (id: string) => Promise<SharedUser[]>;
    getReminders: (id: string) => Promise<DocumentReminder[]>;
    getReminder: (id: string) => Promise<DocumentReminder>;
    createVersion: (id: string, file: File) => Promise<VersionHistoryResponse>;
    createComment: (id: string, data: { comment: string }) => Promise<DocumentComment>;
    shareDocument: (id: string, data: { user_ids: string[]; start_date?: string; end_date?: string }) => Promise<SharedUser[]>;
    deleteShare: (docId: string, shareId: string) => Promise<{ detail: string }>;
    createReminder: (id: string, data: any) => Promise<DocumentReminder>;
    updateReminder: (id: string, data: any) => Promise<DocumentReminder>;
    deleteReminder: (id: string) => Promise<{ message: string }>;
    downloadDocument: (id: string) => Promise<void>;
    downloadVersion: (docId: string, versionId: string) => Promise<void>;
    updateDocument: (id: string, data: any) => Promise<Document>;
  };
  previewUrlSuffix?: string; // e.g., "" or "/me"
}

export function DocumentDetail({
  documentId,
  backPath,
  permissions,
  apiFunctions,
  previewUrlSuffix = ''
}: DocumentDetailProps) {
  const router = useRouter();
  const { hasAnyPermission } = usePermissions();
  const { user } = useAuth();

  const [document, setDocument] = useState<Document | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [accessDenied, setAccessDenied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [activeTab, setActiveTab] = useState('details');
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [isLoadingVersions, setIsLoadingVersions] = useState(false);
  const [isUploadingVersion, setIsUploadingVersion] = useState(false);
  const [comments, setComments] = useState<DocumentComment[]>([]);
  const [isLoadingComments, setIsLoadingComments] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [isSubmittingComment, setIsSubmittingComment] = useState(false);
  const [sharedUsers, setSharedUsers] = useState<SharedUser[]>([]);
  const [isLoadingSharedUsers, setIsLoadingSharedUsers] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
  const [shareStartDate, setShareStartDate] = useState('');
  const [shareEndDate, setShareEndDate] = useState('');
  const [isSharingDocument, setIsSharingDocument] = useState(false);
  const [availableUsers, setAvailableUsers] = useState<UserBasicId[]>([]);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);
  const [deletingShareId, setDeletingShareId] = useState<string | null>(null);
  const [showDeleteConfirmModal, setShowDeleteConfirmModal] = useState(false);
  const [shareToDelete, setShareToDelete] = useState<SharedUser | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Reminder state
  const [reminders, setReminders] = useState<DocumentReminder[]>([]);
  const [isLoadingReminders, setIsLoadingReminders] = useState(false);
  const [showReminderModal, setShowReminderModal] = useState(false);
  const [editingReminder, setEditingReminder] = useState<DocumentReminder | null>(null);
  const [reminderDate, setReminderDate] = useState('');
  const [reminderTime, setReminderTime] = useState('');
  const [reminderSubject, setReminderSubject] = useState('');
  const [reminderMessage, setReminderMessage] = useState('');
  const [reminderAssignedUserIds, setReminderAssignedUserIds] = useState<string[]>([]);
  const [isSubmittingReminder, setIsSubmittingReminder] = useState(false);
  const [reminderAvailableUsers, setReminderAvailableUsers] = useState<UserBasicId[]>([]);
  const [isLoadingReminderUsers, setIsLoadingReminderUsers] = useState(false);
  const [showViewReminderModal, setShowViewReminderModal] = useState(false);
  const [selectedReminder, setSelectedReminder] = useState<DocumentReminder | null>(null);
  const [isLoadingReminderDetail, setIsLoadingReminderDetail] = useState(false);
  const [showDeleteReminderModal, setShowDeleteReminderModal] = useState(false);
  const [reminderToDelete, setReminderToDelete] = useState<DocumentReminder | null>(null);
  const [isDeletingReminder, setIsDeletingReminder] = useState(false);

  // Toast notification state
  const [toast, setToast] = useState<{
    message: string;
    type: 'success' | 'error' | 'info' | 'warning';
    isVisible: boolean;
  }>({
    message: '',
    type: 'success',
    isVisible: false,
  });

  // Check permissions
  const canViewDocuments = hasAnyPermission([permissions.view]);
  const canViewVersions = hasAnyPermission([permissions.viewVersion]);
  const canCreateVersion = hasAnyPermission([permissions.createVersion]);
  const canViewComments = hasAnyPermission([permissions.viewComments]);
  const canCreateComment = hasAnyPermission([permissions.createComment]);
  const canShareDocument = hasAnyPermission([permissions.share]);
  const canViewSharedUsers = hasAnyPermission([permissions.viewShared]);
  const canDeleteShare = hasAnyPermission([permissions.deleteShare]);
  const canViewReminders = hasAnyPermission([permissions.viewReminders]);
  const canCreateReminder = hasAnyPermission([permissions.createReminder]);
  const canViewReminderDetail = hasAnyPermission([permissions.viewReminderDetail]);
  const canUpdateReminder = hasAnyPermission([permissions.updateReminder]);
  const canDeleteReminder = hasAnyPermission([permissions.deleteReminder]);

  // Helper function to check if current user is the owner of the document
  const isDocumentOwner = (doc: Document | null) => {
    return doc && user && doc.created_by === user.id;
  };

  // Helper function to check if current user is the creator of a reminder
  const isReminderCreator = (reminder: DocumentReminder) => {
    return user && reminder.created_by === user.id;
  };

  const fetchDocument = async () => {
    if (!canViewDocuments) {
      setAccessDenied(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const data = await apiFunctions.getDocument(documentId);
      setDocument(data);
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError.status === 403) {
        setAccessDenied(true);
      } else {
        setError(apiError.detail || 'Failed to load document');
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocument();
  }, [documentId, canViewDocuments]);

  const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
    setToast({ message, type, isVisible: true });
  };

  const hideToast = () => {
    setToast((prev) => ({ ...prev, isVisible: false }));
  };

  const handleEditSuccess = () => {
    showToast('Document updated successfully', 'success');
    fetchDocument();
  };

  const fetchVersionHistory = async () => {
    if (!canViewVersions) return;
    setIsLoadingVersions(true);
    try {
      const data = await apiFunctions.getVersions(documentId);
      setVersions(data);
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || 'Failed to load version history', 'error');
    } finally {
      setIsLoadingVersions(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'versions' && canViewVersions && versions.length === 0) {
      fetchVersionHistory();
    }
  }, [activeTab, canViewVersions]);

  const fetchComments = async () => {
    if (!canViewComments) return;
    setIsLoadingComments(true);
    try {
      const data = await apiFunctions.getComments(documentId);
      setComments(data);
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || 'Failed to load comments', 'error');
    } finally {
      setIsLoadingComments(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'comments' && canViewComments && comments.length === 0) {
      fetchComments();
    }
  }, [activeTab, canViewComments]);

  const fetchSharedUsers = async () => {
    if (!canViewSharedUsers) return;
    setIsLoadingSharedUsers(true);
    try {
      const data = await apiFunctions.getSharedUsers(documentId);
      setSharedUsers(data);
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || 'Failed to load shared users', 'error');
    } finally {
      setIsLoadingSharedUsers(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'share' && canViewSharedUsers && sharedUsers.length === 0) {
      fetchSharedUsers();
    }
  }, [activeTab, canViewSharedUsers]);

  const fetchReminders = async () => {
    if (!canViewReminders) return;
    setIsLoadingReminders(true);
    try {
      const data = await apiFunctions.getReminders(documentId);
      setReminders(data);
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || 'Failed to load reminders', 'error');
    } finally {
      setIsLoadingReminders(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'reminders' && canViewReminders && reminders.length === 0) {
      fetchReminders();
    }
  }, [activeTab, canViewReminders]);

  const fetchAvailableUsers = async () => {
    setIsLoadingUsers(true);
    try {
      const response = await api.getUsersForAssignment();
      setAvailableUsers(response);
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || 'Failed to load users', 'error');
    } finally {
      setIsLoadingUsers(false);
    }
  };

  const handleShareDocument = async () => {
    if (selectedUserIds.length === 0) {
      showToast('Please select at least one user', 'warning');
      return;
    }

    setIsSharingDocument(true);
    try {
      await apiFunctions.shareDocument(documentId, {
        user_ids: selectedUserIds,
        start_date: shareStartDate || undefined,
        end_date: shareEndDate || undefined,
      });
      showToast('Document shared successfully', 'success');
      setShowShareModal(false);
      setSelectedUserIds([]);
      setShareStartDate('');
      setShareEndDate('');
      fetchSharedUsers();
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || 'Failed to share document', 'error');
    } finally {
      setIsSharingDocument(false);
    }
  };

  const handleDeleteShareClick = (sharedUser: SharedUser) => {
    setShareToDelete(sharedUser);
    setShowDeleteConfirmModal(true);
  };

  const handleConfirmDelete = async () => {
    if (!shareToDelete) return;

    setDeletingShareId(shareToDelete.id);
    try {
      await apiFunctions.deleteShare(documentId, shareToDelete.id);
      showToast('Share deleted successfully', 'success');
      setShowDeleteConfirmModal(false);
      setShareToDelete(null);
      fetchSharedUsers();
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || 'Failed to delete share', 'error');
    } finally {
      setDeletingShareId(null);
    }
  };

  const handleCancelDelete = () => {
    setShowDeleteConfirmModal(false);
    setShareToDelete(null);
  };

  const fetchReminderAvailableUsers = async () => {
    setIsLoadingReminderUsers(true);
    try {
      const response = await api.getUsersForAssignment();
      setReminderAvailableUsers(response);
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || 'Failed to load users', 'error');
    } finally {
      setIsLoadingReminderUsers(false);
    }
  };

  const handleViewReminder = async (reminderId: string) => {
    setIsLoadingReminderDetail(true);
    setShowViewReminderModal(true);
    try {
      const data = await apiFunctions.getReminder(reminderId);
      setSelectedReminder(data);
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || 'Failed to load reminder details', 'error');
      setShowViewReminderModal(false);
    } finally {
      setIsLoadingReminderDetail(false);
    }
  };

  const handleEditReminder = async (reminderId: string) => {
    try {
      let users = reminderAvailableUsers;
      if (users.length === 0) {
        const response = await api.getUsersForAssignment();
        users = response;
        setReminderAvailableUsers(users);
      }

      const data = await apiFunctions.getReminder(reminderId);
      setEditingReminder(data);
      setReminderDate(data.date);
      setReminderTime(data.time);
      setReminderSubject(data.subject);
      setReminderMessage(data.message);

      const userIds = data.assigned_users
        .map((user: { username: string }) => {
          const foundUser = users.find(u => u.username === user.username);
          return foundUser?.id || '';
        })
        .filter(id => id !== '');

      setReminderAssignedUserIds(userIds);
      setShowReminderModal(true);
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || 'Failed to load reminder for editing', 'error');
    }
  };

  const handleDeleteReminderClick = (reminder: DocumentReminder) => {
    setReminderToDelete(reminder);
    setShowDeleteReminderModal(true);
  };

  const handleConfirmDeleteReminder = async () => {
    if (!reminderToDelete) return;

    setIsDeletingReminder(true);
    try {
      await apiFunctions.deleteReminder(reminderToDelete.id);
      showToast('Reminder deleted successfully', 'success');
      setShowDeleteReminderModal(false);
      setReminderToDelete(null);
      fetchReminders();
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || 'Failed to delete reminder', 'error');
    } finally {
      setIsDeletingReminder(false);
    }
  };

  const handleCancelDeleteReminder = () => {
    setShowDeleteReminderModal(false);
    setReminderToDelete(null);
  };

  const handleSubmitReminder = async () => {
    if (!reminderDate || !reminderTime || !reminderSubject.trim() || !reminderMessage.trim()) {
      showToast('Please fill in all required fields', 'warning');
      return;
    }
    if (reminderAssignedUserIds.length === 0) {
      showToast('Please assign at least one user', 'warning');
      return;
    }

    setIsSubmittingReminder(true);
    try {
      const reminderData = {
        date: reminderDate,
        time: reminderTime,
        subject: reminderSubject,
        message: reminderMessage,
        assign_user: reminderAssignedUserIds,
      };

      if (editingReminder) {
        await apiFunctions.updateReminder(editingReminder.id, reminderData);
        showToast('Reminder updated successfully', 'success');
      } else {
        await apiFunctions.createReminder(documentId, reminderData);
        showToast('Reminder created successfully', 'success');
      }

      setShowReminderModal(false);
      setEditingReminder(null);
      setReminderDate('');
      setReminderTime('');
      setReminderSubject('');
      setReminderMessage('');
      setReminderAssignedUserIds([]);
      fetchReminders();
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || `Failed to ${editingReminder ? 'update' : 'create'} reminder`, 'error');
    } finally {
      setIsSubmittingReminder(false);
    }
  };

  const handleAddComment = async () => {
    if (!newComment.trim()) {
      showToast('Comment cannot be empty', 'warning');
      return;
    }

    setIsSubmittingComment(true);
    try {
      await apiFunctions.createComment(documentId, { comment: newComment });
      showToast('Comment added successfully', 'success');
      setNewComment('');
      fetchComments();
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || 'Failed to add comment', 'error');
    } finally {
      setIsSubmittingComment(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploadingVersion(true);
    try {
      await apiFunctions.createVersion(documentId, file);
      showToast('New version uploaded successfully', 'success');
      fetchVersionHistory();
    } catch (err) {
      const error = err as ApiError;
      showToast(error.detail || 'Failed to upload new version', 'error');
    } finally {
      setIsUploadingVersion(false);
      event.target.value = '';
    }
  };

  if (isLoading) {
    return <LoadingOverlay message="Loading document details..." />;
  }

  if (accessDenied) {
    return <AccessDenied resource="document details" />;
  }

  if (error || !document) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Document Not Found</h2>
          <p className="text-gray-600 mb-6">{error || 'The document you are looking for does not exist.'}</p>
          <Button onClick={() => router.push(backPath)}>
            Back to Documents
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Button
              variant="secondary"
              onClick={() => router.push(backPath)}
              className="p-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </Button>
            <h1 className="text-2xl font-bold">{document.name}</h1>
          </div>
          <p className="text-gray-500 ml-14">View and manage document details</p>
        </div>
        <div className="flex gap-2">
          <CanAccess permission={permissions.view}>
            <Button
              variant="secondary"
              onClick={() => {
                const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const token = localStorage.getItem('token');
                const url = `${API_BASE_URL}/api/v1/documents/${documentId}/preview${previewUrlSuffix}`;

                if (token) {
                  fetch(url, { headers: { 'X-Session-Key': token } })
                    .then(response => response.blob())
                    .then(blob => {
                      const blobUrl = window.URL.createObjectURL(blob);
                      window.open(blobUrl, '_blank');
                    })
                    .catch(() => showToast('Failed to preview document', 'error'));
                } else {
                  showToast('Authentication required', 'error');
                }
              }}
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              Preview
            </Button>
          </CanAccess>
          <CanAccess permission={permissions.view}>
            <Button
              variant="secondary"
              onClick={async () => {
                try {
                  await apiFunctions.downloadDocument(documentId);
                } catch (err) {
                  const error = err as Error;
                  showToast(error.message || 'Failed to download document', 'error');
                }
              }}
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download
            </Button>
          </CanAccess>
          {isDocumentOwner(document) && (
            <CanAccess permission={permissions.edit}>
              <Button onClick={() => setShowEditModal(true)}>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Edit Document
              </Button>
            </CanAccess>
          )}
        </div>
      </div>

      <Tabs
        tabs={[
          { key: 'details', label: 'Details' },
          ...(canViewVersions ? [{ key: 'versions', label: 'Version History' }] : []),
          ...(canViewComments ? [{ key: 'comments', label: 'Comments' }] : []),
          ...(canViewSharedUsers ? [{ key: 'share', label: 'Shared Users' }] : []),
          ...(canViewReminders ? [{ key: 'reminders', label: 'Reminders' }] : []),
        ]}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      >
        {activeTab === 'details' && (
          <div className="grid gap-6">
            <Card>
              <CardHeader title="Document Information" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Document Name</label>
                  <p className="text-gray-900">{document.name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <p className="text-gray-900">{document.category?.title || '-'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Subcategory</label>
                  <p className="text-gray-900">{document.subcategory?.title || '-'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Stage</label>
                  {document.stage?.title ? (
                    <Badge color={document.stage.color}>{document.stage.title}</Badge>
                  ) : (
                    <p className="text-gray-400">-</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Assigned To</label>
                  <p className="text-gray-900">{document.assigned_user?.username || 'Unassigned'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Created By</label>
                  <p className="text-gray-900">{document.creator?.username || 'Unknown'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Created At</label>
                  <p className="text-gray-900">
                    {document.created_at ? formatDateTime(document.created_at) : '-'}
                  </p>
                </div>
                {document.updated_at && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Last Updated</label>
                    <p className="text-gray-900">{formatDateTime(document.updated_at)}</p>
                  </div>
                )}
              </div>
            </Card>

            {document.description && (
              <Card>
                <CardHeader title="Description" />
                <p className="text-gray-700 whitespace-pre-wrap">{document.description}</p>
              </Card>
            )}

            {document.tags && document.tags.length > 0 && (
              <Card>
                <CardHeader title="Tags" />
                <div className="flex flex-wrap gap-2">
                  {document.tags.map((tag) => (
                    <span
                      key={tag.id}
                      className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-700"
                    >
                      {tag.title}
                    </span>
                  ))}
                </div>
              </Card>
            )}
          </div>
        )}

        {activeTab === 'versions' && canViewVersions && (
          <div>
            <Card>
              <div className="flex items-center justify-between mb-6">
                <CardHeader title="Version History" />
                {canCreateVersion && (
                  <div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      className="hidden"
                      onChange={handleFileUpload}
                      disabled={isUploadingVersion}
                    />
                    <Button
                      onClick={() => fileInputRef.current?.click()}
                      disabled={isUploadingVersion}
                    >
                      {isUploadingVersion ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                          Uploading...
                        </>
                      ) : (
                        <>
                          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                          </svg>
                          Upload New Version
                        </>
                      )}
                    </Button>
                  </div>
                )}
              </div>
              {isLoadingVersions ? (
                <div className="flex justify-center items-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : versions.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No version history available
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Version</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Uploaded By</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Uploaded At</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {versions.map((version) => (
                        <tr key={version.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            v{version.version_number}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {version.creator?.username}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {formatDateTime(version.created_at)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {version.is_current ? (
                              <Badge variant="success">Current</Badge>
                            ) : (
                              <span className="text-sm text-gray-500">Previous</span>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            <div className="flex gap-3">
                              <button
                                onClick={() => {
                                  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                                  const token = localStorage.getItem('token');
                                  const url = `${API_BASE_URL}/api/v1/documents/${documentId}/versions/${version.id}/preview${previewUrlSuffix}`;

                                  if (token) {
                                    fetch(url, { headers: { 'X-Session-Key': token } })
                                      .then(response => response.blob())
                                      .then(blob => {
                                        const blobUrl = window.URL.createObjectURL(blob);
                                        window.open(blobUrl, '_blank');
                                      })
                                      .catch(() => showToast('Failed to preview version', 'error'));
                                  } else {
                                    showToast('Authentication required', 'error');
                                  }
                                }}
                                className="text-blue-600 hover:text-blue-800 transition-colors"
                                title="Preview this version"
                              >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                </svg>
                              </button>
                              <button
                                onClick={async () => {
                                  try {
                                    await apiFunctions.downloadVersion(documentId, version.id);
                                  } catch (err) {
                                    const error = err as Error;
                                    showToast(error.message || 'Failed to download version', 'error');
                                  }
                                }}
                                className="text-blue-600 hover:text-blue-800 transition-colors"
                                title="Download this version"
                              >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        )}

        {activeTab === 'comments' && canViewComments && (
          <div>
            <Card>
              <CardHeader title="Comments" />
              {canCreateComment && (
                <div className="mb-6 pb-6 border-b border-gray-200">
                  <div className="space-y-3">
                    <textarea
                      value={newComment}
                      onChange={(e) => setNewComment(e.target.value)}
                      placeholder="Write a comment..."
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                      rows={3}
                      disabled={isSubmittingComment}
                    />
                    <div className="flex justify-end">
                      <Button
                        onClick={handleAddComment}
                        disabled={isSubmittingComment || !newComment.trim()}
                      >
                        {isSubmittingComment ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                            Posting...
                          </>
                        ) : (
                          <>
                            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                            </svg>
                            Add Comment
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </div>
              )}
              {isLoadingComments ? (
                <div className="flex justify-center items-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : comments.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No comments available
                </div>
              ) : (
                <div className="space-y-4">
                  {comments.map((comment) => (
                    <div key={comment.id} className="border-b border-gray-200 last:border-0 pb-4 last:pb-0">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                            <span className="text-sm font-medium text-blue-600">
                              {comment.user.username.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">{comment.user.username}</p>
                            <p className="text-xs text-gray-500">{formatDateTime(comment.created_at)}</p>
                          </div>
                        </div>
                      </div>
                      <p className="text-sm text-gray-700 ml-10 whitespace-pre-wrap">{comment.comment}</p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        )}

        {activeTab === 'share' && canViewSharedUsers && (
          <div>
            <Card>
              <div className="flex items-center justify-between mb-6">
                <CardHeader title="Shared Users" />
                {canShareDocument && (
                  <Button
                    onClick={() => {
                      setShowShareModal(true);
                      fetchAvailableUsers();
                    }}
                  >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                    </svg>
                    Share Document
                  </Button>
                )}
              </div>
              {isLoadingSharedUsers ? (
                <div className="flex justify-center items-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : sharedUsers.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  This document has not been shared with anyone yet
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Start Date</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">End Date</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Assigned At</th>
                        {canDeleteShare && isDocumentOwner(document) && (
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                        )}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {sharedUsers.map((sharedUser) => (
                        <tr key={sharedUser.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                                <span className="text-sm font-medium text-blue-600">
                                  {sharedUser.user.username.charAt(0).toUpperCase()}
                                </span>
                              </div>
                              <span className="text-sm font-medium text-gray-900">{sharedUser.user.username}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {sharedUser.start_date || '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {sharedUser.end_date || '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {formatDateTime(sharedUser.created_at)}
                          </td>
                          {canDeleteShare && isDocumentOwner(document) && (
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              <button
                                onClick={() => handleDeleteShareClick(sharedUser)}
                                disabled={deletingShareId === sharedUser.id}
                                className="text-red-600 hover:text-red-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                title="Revoke access"
                              >
                                {deletingShareId === sharedUser.id ? (
                                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-red-600"></div>
                                ) : (
                                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                  </svg>
                                )}
                              </button>
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        )}

        {activeTab === 'reminders' && canViewReminders && (
          <div>
            <Card>
              <div className="flex items-center justify-between mb-6">
                <CardHeader title="Reminders" />
                {canCreateReminder && (
                  <Button
                    onClick={() => {
                      setEditingReminder(null);
                      setReminderDate('');
                      setReminderTime('');
                      setReminderSubject('');
                      setReminderMessage('');
                      setReminderAssignedUserIds([]);
                      setShowReminderModal(true);
                      fetchReminderAvailableUsers();
                    }}
                  >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    Create Reminder
                  </Button>
                )}
              </div>
              {isLoadingReminders ? (
                <div className="flex justify-center items-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : reminders.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No reminders available for this document
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Subject</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date & Time</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Assigned Users</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created By</th>
                        {(canViewReminderDetail || canUpdateReminder || canDeleteReminder) && (
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                        )}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {reminders.map((reminder) => (
                        <tr key={reminder.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900">{reminder.subject}</div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm text-gray-900">{reminder.date}</div>
                            <div className="text-sm text-gray-500">{reminder.time}</div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex flex-wrap gap-1">
                              {reminder.assigned_users.map((user: { username: string }, index: number) => (
                                <span
                                  key={index}
                                  className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                                >
                                  {user.username}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {reminder.creator.username}
                          </td>
                          {(canViewReminderDetail || canUpdateReminder || canDeleteReminder) && (
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              <div className="flex gap-3">
                                {canViewReminderDetail && (
                                  <button
                                    onClick={() => handleViewReminder(reminder.id)}
                                    className="text-blue-600 hover:text-blue-800 transition-colors"
                                    title="View details"
                                  >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                    </svg>
                                  </button>
                                )}
                                {canUpdateReminder && isReminderCreator(reminder) && (
                                  <button
                                    onClick={() => handleEditReminder(reminder.id)}
                                    className="text-green-600 hover:text-green-800 transition-colors"
                                    title="Edit reminder"
                                  >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                    </svg>
                                  </button>
                                )}
                                {canDeleteReminder && isReminderCreator(reminder) && (
                                  <button
                                    onClick={() => handleDeleteReminderClick(reminder)}
                                    className="text-red-600 hover:text-red-800 transition-colors"
                                    title="Delete reminder"
                                  >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                  </button>
                                )}
                              </div>
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        )}
      </Tabs>

      <DocumentModal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        document={document}
        onSuccess={handleEditSuccess}
        updateFn={apiFunctions.updateDocument}
      />

      <Modal
        isOpen={showShareModal}
        onClose={() => {
          setShowShareModal(false);
          setSelectedUserIds([]);
          setShareStartDate('');
          setShareEndDate('');
        }}
        title="Share Document"
        size="xl"
      >
        <>
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Select Users</label>
              {isLoadingUsers ? (
                <div className="flex justify-center items-center py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                <div className="border border-gray-300 rounded-lg max-h-60 overflow-y-auto">
                  {availableUsers.map((user) => (
                    <label
                      key={user.id}
                      className="flex items-center gap-3 p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
                    >
                      <input
                        type="checkbox"
                        checked={selectedUserIds.includes(user.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedUserIds([...selectedUserIds, user.id]);
                          } else {
                            setSelectedUserIds(selectedUserIds.filter((id) => id !== user.id));
                          }
                        }}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                          <span className="text-sm font-medium text-blue-600">
                            {user.username.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">{user.username}</p>
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Start Date (Optional)</label>
              <input
                type="date"
                value={shareStartDate}
                onChange={(e) => setShareStartDate(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">End Date (Optional)</label>
              <input
                type="date"
                value={shareEndDate}
                onChange={(e) => setShareEndDate(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 mt-6">
            <Button
              variant="secondary"
              onClick={() => {
                setShowShareModal(false);
                setSelectedUserIds([]);
                setShareStartDate('');
                setShareEndDate('');
              }}
              disabled={isSharingDocument}
            >
              Cancel
            </Button>
            <Button
              onClick={handleShareDocument}
              disabled={isSharingDocument || selectedUserIds.length === 0}
            >
              {isSharingDocument ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Sharing...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                  </svg>
                  Share Document
                </>
              )}
            </Button>
          </div>
        </>
      </Modal>

      <Modal isOpen={showDeleteConfirmModal} onClose={handleCancelDelete} size="md">
        <div className="flex items-center justify-center w-12 h-12 mx-auto mb-4 bg-red-100 rounded-full">
          <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 text-center mb-2">Revoke Access</h3>
        <p className="text-sm text-gray-600 text-center mb-6">
          Are you sure you want to revoke access for <span className="font-semibold">{shareToDelete?.user.username}</span>?
          This user will no longer be able to view this document.
        </p>
        <div className="flex items-center justify-end gap-3">
          <Button variant="secondary" onClick={handleCancelDelete} disabled={deletingShareId === shareToDelete?.id}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirmDelete}
            disabled={deletingShareId === shareToDelete?.id}
            className="bg-red-600 hover:bg-red-700 focus:ring-red-500"
          >
            {deletingShareId === shareToDelete?.id ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Revoking...
              </>
            ) : (
              <>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Revoke Access
              </>
            )}
          </Button>
        </div>
      </Modal>

      <Modal
        isOpen={showReminderModal}
        onClose={() => {
          setShowReminderModal(false);
          setEditingReminder(null);
          setReminderDate('');
          setReminderTime('');
          setReminderSubject('');
          setReminderMessage('');
          setReminderAssignedUserIds([]);
        }}
        title={editingReminder ? 'Edit Reminder' : 'Create Reminder'}
        size="xl"
      >
        <>
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Date <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  value={reminderDate}
                  onChange={(e) => setReminderDate(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={isSubmittingReminder}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Time <span className="text-red-500">*</span>
                </label>
                <input
                  type="time"
                  value={reminderTime}
                  onChange={(e) => setReminderTime(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={isSubmittingReminder}
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Subject <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={reminderSubject}
                onChange={(e) => setReminderSubject(e.target.value)}
                placeholder="Enter reminder subject"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isSubmittingReminder}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Message <span className="text-red-500">*</span>
              </label>
              <textarea
                value={reminderMessage}
                onChange={(e) => setReminderMessage(e.target.value)}
                placeholder="Enter reminder message"
                rows={4}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                disabled={isSubmittingReminder}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Assign Users <span className="text-red-500">*</span>
              </label>
              {isLoadingReminderUsers ? (
                <div className="flex justify-center items-center py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                <div className="border border-gray-300 rounded-lg max-h-60 overflow-y-auto">
                  {reminderAvailableUsers.map((user) => (
                    <label
                      key={user.id}
                      className="flex items-center gap-3 p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
                    >
                      <input
                        type="checkbox"
                        checked={reminderAssignedUserIds.includes(user.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setReminderAssignedUserIds([...reminderAssignedUserIds, user.id]);
                          } else {
                            setReminderAssignedUserIds(reminderAssignedUserIds.filter((id) => id !== user.id));
                          }
                        }}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        disabled={isSubmittingReminder}
                      />
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                          <span className="text-sm font-medium text-blue-600">
                            {user.username.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">{user.username}</p>
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 mt-6">
            <Button
              variant="secondary"
              onClick={() => {
                setShowReminderModal(false);
                setEditingReminder(null);
                setReminderDate('');
                setReminderTime('');
                setReminderSubject('');
                setReminderMessage('');
                setReminderAssignedUserIds([]);
              }}
              disabled={isSubmittingReminder}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmitReminder}
              disabled={
                isSubmittingReminder ||
                !reminderDate ||
                !reminderTime ||
                !reminderSubject.trim() ||
                !reminderMessage.trim() ||
                reminderAssignedUserIds.length === 0
              }
            >
              {isSubmittingReminder ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  {editingReminder ? 'Updating...' : 'Creating...'}
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d={editingReminder
                        ? "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                        : "M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                      }
                    />
                  </svg>
                  {editingReminder ? 'Update Reminder' : 'Create Reminder'}
                </>
              )}
            </Button>
          </div>
        </>
      </Modal>

      <Modal
        isOpen={showViewReminderModal}
        onClose={() => {
          setShowViewReminderModal(false);
          setSelectedReminder(null);
        }}
        title="Reminder Details"
        size="lg"
      >
        {isLoadingReminderDetail ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : selectedReminder ? (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
              <p className="text-gray-900 text-base">{selectedReminder.subject}</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                <p className="text-gray-900">{selectedReminder.date}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Time</label>
                <p className="text-gray-900">{selectedReminder.time}</p>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Message</label>
              <p className="text-gray-900 whitespace-pre-wrap">{selectedReminder.message}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Assigned Users</label>
              <div className="flex flex-wrap gap-2">
                {selectedReminder.assigned_users.map((user: { username: string }, index: number) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800"
                  >
                    {user.username}
                  </span>
                ))}
              </div>
            </div>
            <div className="border-t border-gray-200 pt-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Created By</label>
                  <p className="text-gray-900">{selectedReminder.creator.username}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Document</label>
                  <p className="text-gray-900">{selectedReminder.document.name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Created At</label>
                  <p className="text-gray-900">{formatDateTime(selectedReminder.created_at)}</p>
                </div>
                {selectedReminder.updated_at && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Updated At</label>
                    <p className="text-gray-900">{formatDateTime(selectedReminder.updated_at)}</p>
                  </div>
                )}
              </div>
            </div>
            <div className="flex justify-end pt-4 border-t border-gray-200">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowViewReminderModal(false);
                  setSelectedReminder(null);
                }}
              >
                Close
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal isOpen={showDeleteReminderModal} onClose={handleCancelDeleteReminder} size="md">
        <div className="flex items-center justify-center w-12 h-12 mx-auto mb-4 bg-red-100 rounded-full">
          <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 text-center mb-2">Delete Reminder</h3>
        <p className="text-sm text-gray-600 text-center mb-6">
          Are you sure you want to delete the reminder <span className="font-semibold">&quot;{reminderToDelete?.subject}&quot;</span>?
          This action cannot be undone.
        </p>
        <div className="flex items-center justify-end gap-3">
          <Button variant="secondary" onClick={handleCancelDeleteReminder} disabled={isDeletingReminder}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirmDeleteReminder}
            disabled={isDeletingReminder}
            className="bg-red-600 hover:bg-red-700 focus:ring-red-500"
          >
            {isDeletingReminder ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Deleting...
              </>
            ) : (
              <>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete Reminder
              </>
            )}
          </Button>
        </div>
      </Modal>

      <Toast
        message={toast.message}
        type={toast.type}
        isVisible={toast.isVisible}
        onClose={hideToast}
      />
    </div>
  );
}
