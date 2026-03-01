'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardHeader, LoadingOverlay, Button, Toast, Pagination, Modal } from '@/components/ui';
import { AccessDenied } from '@/components/auth/AccessDenied';
import { usePermissions } from '@/hooks/usePermissions';
import { useAuth } from '@/hooks/useAuth';
import { api } from '@/lib/api';
import { DocumentReminder, ApiError, Document, UserBasicId } from '@/types';
import { formatDateTime } from '@/lib/utils';

interface RemindersListProps {
  title: string;
  description: string;
  permissions: {
    list: string;
      listMy?: string;
    view: string;
    viewMy?: string;
    delete: string;
    deleteMy?: string;
    create: string;
    createMy?: string;
    update: string;
    updateMy?: string;
  };
  apiFunctions: {
    getReminders: typeof api.getReminders;
    getReminder: typeof api.getReminder;
    deleteReminder: typeof api.deleteReminder;
    updateReminder: typeof api.updateReminder;
    createDocumentReminder: typeof api.createDocumentReminder;
    getDocuments: typeof api.getDocuments;
  };
}

export function RemindersList({ title, description, permissions, apiFunctions }: RemindersListProps) {
  const router = useRouter();
  const { hasAnyPermission } = usePermissions();
  const { user } = useAuth();

  const [reminders, setReminders] = useState<DocumentReminder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [accessDenied, setAccessDenied] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalRows, setTotalRows] = useState(0);
  const pageSize = 20;

  // View reminder state
  const [showViewReminderModal, setShowViewReminderModal] = useState(false);
  const [selectedReminder, setSelectedReminder] = useState<DocumentReminder | null>(null);
  const [isLoadingReminderDetail, setIsLoadingReminderDetail] = useState(false);

  // Delete reminder state
  const [showDeleteReminderModal, setShowDeleteReminderModal] = useState(false);
  const [reminderToDelete, setReminderToDelete] = useState<DocumentReminder | null>(null);
  const [isDeletingReminder, setIsDeletingReminder] = useState(false);

  // Create/Edit reminder state
  const [showReminderFormModal, setShowReminderFormModal] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [currentReminderId, setCurrentReminderId] = useState<string | null>(null);
  const [isSavingReminder, setIsSavingReminder] = useState(false);
  const [formData, setFormData] = useState({
    document_id: '',
    subject: '',
    date: '',
    time: '',
    message: '',
    assign_user: [] as string[],
  });

  // Dropdown data
  const [documents, setDocuments] = useState<Document[]>([]);
  const [users, setUsers] = useState<UserBasicId[]>([]);
  const [isLoadingDropdowns, setIsLoadingDropdowns] = useState(false);

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
  const canViewReminders = hasAnyPermission([permissions.list, permissions.listMy].filter(Boolean) as string[]);
  const canViewReminderDetail = hasAnyPermission([permissions.view, permissions.viewMy].filter(Boolean) as string[]);
  const canDeleteReminder = hasAnyPermission([permissions.delete, permissions.deleteMy].filter(Boolean) as string[]);
  const canCreateReminder = hasAnyPermission([permissions.create, permissions.createMy].filter(Boolean) as string[]);
  const canEditReminder = hasAnyPermission([permissions.update, permissions.updateMy].filter(Boolean) as string[]);

  // Helper function to check if current user is the creator of a reminder
  const isReminderCreator = (reminder: DocumentReminder) => {
    return user && reminder.created_by === user.id;
  };

  const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
    setToast({ message, type, isVisible: true });
  };

  const hideToast = () => {
    setToast((prev) => ({ ...prev, isVisible: false }));
  };

  const fetchReminders = async () => {
    if (!canViewReminders) {
      setAccessDenied(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const response = await apiFunctions.getReminders({
        page: currentPage,
        page_size: pageSize,
      });
      setReminders(response.data);
      setTotalPages(response.total_pages ?? 1);
      setTotalRows(response.total ?? 0);
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError.status === 403) {
        setAccessDenied(true);
      } else {
        showToast(apiError.detail || 'Failed to load reminders', 'error');
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReminders();
  }, [currentPage, canViewReminders]);

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

  const fetchDropdownData = async () => {
    setIsLoadingDropdowns(true);
    try {
      const [docsResponse, usersResponse] = await Promise.all([
        apiFunctions.getDocuments({ page: 1, page_size: 1000, archive: false }),
        api.getUsersForAssignment(),
      ]);
      setDocuments(docsResponse.data);
      setUsers(usersResponse);
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || 'Failed to load dropdown data', 'error');
    } finally {
      setIsLoadingDropdowns(false);
    }
  };

  const handleCreateReminderClick = () => {
    setIsEditMode(false);
    setCurrentReminderId(null);
    setFormData({
      document_id: '',
      subject: '',
      date: '',
      time: '',
      message: '',
      assign_user: [],
    });
    fetchDropdownData();
    setShowReminderFormModal(true);
  };

  const handleEditReminderClick = async (reminder: DocumentReminder) => {
    setIsEditMode(true);
    setCurrentReminderId(reminder.id);
    setIsLoadingReminderDetail(true);
    setShowReminderFormModal(true);

    try {
      // Fetch dropdown data first
      const [docsResponse, usersResponse] = await Promise.all([
        apiFunctions.getDocuments({ page: 1, page_size: 1000, archive: false }),
        api.getUsersForAssignment(),
      ]);
      setDocuments(docsResponse.data);
      setUsers(usersResponse);

      const data = await apiFunctions.getReminder(reminder.id);

      // Map usernames to user IDs
      const assignedUserIds = data.assigned_users
        .map((assignedUser: { username: string }) => {
          const user = usersResponse.find((u) => u.username === assignedUser.username);
          return user?.id;
        })
        .filter((id): id is string => id !== undefined);

      setFormData({
        document_id: data.document_id,
        subject: data.subject,
        date: data.date,
        time: data.time,
        message: data.message,
        assign_user: assignedUserIds,
      });
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || 'Failed to load reminder details', 'error');
      setShowReminderFormModal(false);
    } finally {
      setIsLoadingReminderDetail(false);
    }
  };

  const handleFormChange = (field: string, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleUserSelection = (userId: string) => {
    setFormData((prev) => {
      const isSelected = prev.assign_user.includes(userId);
      return {
        ...prev,
        assign_user: isSelected
          ? prev.assign_user.filter((id) => id !== userId)
          : [...prev.assign_user, userId],
      };
    });
  };

  const handleSaveReminder = async () => {
    if (!formData.document_id || !formData.subject || !formData.date || !formData.time || !formData.message.trim()) {
      showToast('Please fill in all required fields', 'error');
      return;
    }

    if (formData.assign_user.length === 0) {
      showToast('Please assign at least one user', 'error');
      return;
    }

    setIsSavingReminder(true);
    try {
      const reminderData = {
        date: formData.date,
        time: formData.time,
        subject: formData.subject,
        message: formData.message,
        assign_user: formData.assign_user,
      };

      if (isEditMode && currentReminderId) {
        await apiFunctions.updateReminder(currentReminderId, reminderData);
        showToast('Reminder updated successfully', 'success');
      } else {
        await apiFunctions.createDocumentReminder(formData.document_id, reminderData);
        showToast('Reminder created successfully', 'success');
      }

      setShowReminderFormModal(false);
      fetchReminders();
    } catch (err) {
      const apiError = err as ApiError;
      showToast(apiError.detail || 'Failed to save reminder', 'error');
    } finally {
      setIsSavingReminder(false);
    }
  };

  if (isLoading) {
    return <LoadingOverlay message="Loading reminders..." />;
  }

  if (accessDenied) {
    return <AccessDenied resource="reminders" />;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{title}</h1>
          <p className="text-gray-500">{description}</p>
        </div>
        {canCreateReminder && (
          <Button onClick={handleCreateReminderClick}>
            <svg
              className="w-5 h-5 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
            Create Reminder
          </Button>
        )}
      </div>

      <Card>
        <CardHeader title="All Reminders" />

        {reminders.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No reminders found
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Subject
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Document
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date & Time
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Assigned Users
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created By
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created At
                    </th>
                    {(canViewReminderDetail || canEditReminder || canDeleteReminder) && (
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {reminders.map((reminder) => (
                    <tr key={reminder.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {reminder.subject}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {reminder.document.name}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {reminder.date}
                        </div>
                        <div className="text-sm text-gray-500">
                          {reminder.time}
                        </div>
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
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDateTime(reminder.created_at)}
                      </td>
                      {(canViewReminderDetail || canEditReminder || canDeleteReminder) && (
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <div className="flex gap-3">
                            {canViewReminderDetail && (
                              <button
                                onClick={() => handleViewReminder(reminder.id)}
                                className="text-blue-600 hover:text-blue-800 transition-colors"
                                title="View details"
                              >
                                <svg
                                  className="w-5 h-5"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                                  />
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                                  />
                                </svg>
                              </button>
                            )}
                            {canEditReminder && isReminderCreator(reminder) && (
                              <button
                                onClick={() => handleEditReminderClick(reminder)}
                                className="text-green-600 hover:text-green-800 transition-colors"
                                title="Edit reminder"
                              >
                                <svg
                                  className="w-5 h-5"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                                  />
                                </svg>
                              </button>
                            )}
                            {canDeleteReminder && isReminderCreator(reminder) && (
                              <button
                                onClick={() => handleDeleteReminderClick(reminder)}
                                className="text-red-600 hover:text-red-800 transition-colors"
                                title="Delete reminder"
                              >
                                <svg
                                  className="w-5 h-5"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                  />
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

            {/* Pagination */}
            <div className="mt-6 flex items-center justify-between border-t border-gray-200 pt-4">
              <div className="text-sm text-gray-700">
                Showing <span className="font-medium">{(currentPage - 1) * pageSize + 1}</span> to{' '}
                <span className="font-medium">
                  {Math.min(currentPage * pageSize, totalRows)}
                </span>{' '}
                of <span className="font-medium">{totalRows}</span> reminders
              </div>
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setCurrentPage}
              />
            </div>
          </>
        )}
      </Card>

      {/* View Reminder Modal */}
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
            {/* Subject */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Subject
              </label>
              <p className="text-gray-900 text-base">{selectedReminder.subject}</p>
            </div>

            {/* Date and Time */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Date
                </label>
                <p className="text-gray-900">{selectedReminder.date}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Time
                </label>
                <p className="text-gray-900">{selectedReminder.time}</p>
              </div>
            </div>

            {/* Message */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Message
              </label>
              <p className="text-gray-900 whitespace-pre-wrap">{selectedReminder.message}</p>
            </div>

            {/* Assigned Users */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Assigned Users
              </label>
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

            {/* Metadata */}
            <div className="border-t border-gray-200 pt-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Created By
                  </label>
                  <p className="text-gray-900">{selectedReminder.creator.username}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Document
                  </label>
                  <p className="text-gray-900">{selectedReminder.document.name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Created At
                  </label>
                  <p className="text-gray-900">{formatDateTime(selectedReminder.created_at)}</p>
                </div>
                {selectedReminder.updated_at && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Updated At
                    </label>
                    <p className="text-gray-900">{formatDateTime(selectedReminder.updated_at)}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Close Button */}
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

      {/* Delete Reminder Confirmation Modal */}
      <Modal
        isOpen={showDeleteReminderModal}
        onClose={handleCancelDeleteReminder}
        size="md"
      >
        <div className="flex items-center justify-center w-12 h-12 mx-auto mb-4 bg-red-100 rounded-full">
          <svg
            className="w-6 h-6 text-red-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 text-center mb-2">
          Delete Reminder
        </h3>
        <p className="text-sm text-gray-600 text-center mb-6">
          Are you sure you want to delete the reminder <span className="font-semibold">&quot;{reminderToDelete?.subject}&quot;</span>?
          This action cannot be undone.
        </p>
        <div className="flex items-center justify-end gap-3">
          <Button
            variant="secondary"
            onClick={handleCancelDeleteReminder}
            disabled={isDeletingReminder}
          >
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
                <svg
                  className="w-4 h-4 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
                Delete Reminder
              </>
            )}
          </Button>
        </div>
      </Modal>

      {/* Create/Edit Reminder Form Modal */}
      <Modal
        isOpen={showReminderFormModal}
        onClose={() => {
          setShowReminderFormModal(false);
          setFormData({
            document_id: '',
            subject: '',
            date: '',
            time: '',
            message: '',
            assign_user: [],
          });
        }}
        title={isEditMode ? 'Edit Reminder' : 'Create Reminder'}
        size="xl"
      >
        {isLoadingReminderDetail ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Document Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Document <span className="text-red-500">*</span>
              </label>
              {isLoadingDropdowns ? (
                <div className="flex justify-center items-center py-4">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                <select
                  value={formData.document_id}
                  onChange={(e) => handleFormChange('document_id', e.target.value)}
                  disabled={isEditMode}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                >
                  <option value="">Select a document</option>
                  {documents.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Date and Time */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Date <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  value={formData.date}
                  onChange={(e) => handleFormChange('date', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Time <span className="text-red-500">*</span>
                </label>
                <input
                  type="time"
                  value={formData.time}
                  onChange={(e) => handleFormChange('time', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>

            {/* Subject */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Subject <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.subject}
                onChange={(e) => handleFormChange('subject', e.target.value)}
                placeholder="Enter reminder subject"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Message */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Message <span className="text-red-500">*</span>
              </label>
              <textarea
                value={formData.message}
                onChange={(e) => handleFormChange('message', e.target.value)}
                placeholder="Enter reminder message"
                rows={4}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              />
            </div>

            {/* Assigned Users */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Assign Users <span className="text-red-500">*</span>
              </label>
              {isLoadingDropdowns ? (
                <div className="flex justify-center items-center py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                </div>
              ) : users.length === 0 ? (
                <div className="border border-gray-300 rounded-lg p-4">
                  <div className="text-center text-gray-500">No users available</div>
                </div>
              ) : (
                <div className="border border-gray-300 rounded-lg max-h-60 overflow-y-auto">
                  {users.map((user) => (
                    <label
                      key={user.id}
                      className="flex items-center gap-3 p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
                    >
                      <input
                        type="checkbox"
                        checked={formData.assign_user.includes(user.id)}
                        onChange={() => handleUserSelection(user.id)}
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
              {formData.assign_user.length > 0 && (
                <p className="text-sm text-gray-500 mt-2">
                  {formData.assign_user.length} user(s) selected
                </p>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 mt-6">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowReminderFormModal(false);
                  setFormData({
                    document_id: '',
                    subject: '',
                    date: '',
                    time: '',
                    message: '',
                    assign_user: [],
                  });
                }}
                disabled={isSavingReminder}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSaveReminder}
                disabled={isSavingReminder}
              >
                {isSavingReminder ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    {isEditMode ? 'Updating...' : 'Creating...'}
                  </>
                ) : (
                  <>
                    <svg
                      className="w-4 h-4 mr-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d={isEditMode
                          ? "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                          : "M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                        }
                      />
                    </svg>
                    {isEditMode ? 'Update Reminder' : 'Create Reminder'}
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Toast Notification */}
      <Toast
        message={toast.message}
        type={toast.type}
        isVisible={toast.isVisible}
        onClose={hideToast}
      />
    </div>
  );
}