'use client';

import { RemindersList } from '@/components/reminders';
import { api } from '@/lib/api';

export default function RemindersPage() {
  return (
    <RemindersList
      title="Reminders"
      description="View and manage your document reminders"
      permissions={{
        list: 'reminders.list',
        listMy: 'reminders.list_my',
        view: 'reminders.view',
        viewMy: 'reminders.view_my',
        delete: 'reminders.delete',
        deleteMy: 'reminders.delete_my',
        create: 'reminders.create',
        createMy: 'reminders.create_my',
        update: 'reminders.update',
        updateMy: 'reminders.update_my',
      }}
      apiFunctions={{
        getReminders: (filters) => api.getReminders(filters),
        getReminder: (id) => api.getReminder(id),
        deleteReminder: (id) => api.deleteReminder(id),
        updateReminder: (id, data) => api.updateReminder(id, data),
        createDocumentReminder: (docId, data) => api.createDocumentReminder(docId, data),
        getDocuments: (filters) => api.getDocuments(filters),
        getDocumentAssignableUsers: (docId) => api.getDocumentAssignableUsers(docId),
      }}
    />
  );
}