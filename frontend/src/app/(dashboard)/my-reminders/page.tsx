'use client';

import { RemindersList } from '@/components/reminders';
import { api } from '@/lib/api';

export default function MyRemindersPage() {
  return (
    <RemindersList
      title="My Reminders"
      description="View and manage your document reminders"
      permissions={{
        list: 'reminders.list_my',
        view: 'reminders.view_my',
        delete: 'reminders.delete_my',
        create: 'reminders.create_my',
        update: 'reminders.update_my',
      }}
      apiFunctions={{
        getReminders: (filters) => api.getMyReminders(filters),
        getReminder: (id) => api.getMyReminder(id),
        deleteReminder: (id) => api.deleteMyReminder(id),
        updateReminder: (id, data) => api.updateMyReminder(id, data),
        createDocumentReminder: (docId, data) => api.createMyDocumentReminder(docId, data),
        getDocuments: (filters) => api.getMyDocuments(filters),
      }}
    />
  );
}