'use client';

import { RemindersList } from '@/components/reminders';
import { api } from '@/lib/api';

export default function RemindersPage() {
  return (
    <RemindersList
      title="Reminders"
      description="View and manage all document reminders"
      permissions={{
        list: 'reminders.list',
        view: 'reminders.view',
        delete: 'reminders.delete',
        create: 'reminders.create',
        update: 'reminders.update',
      }}
      apiFunctions={{
        getReminders: (filters) => api.getReminders(filters),
        getReminder: (id) => api.getReminder(id),
        deleteReminder: (id) => api.deleteReminder(id),
        updateReminder: (id, data) => api.updateReminder(id, data),
        createDocumentReminder: (docId, data) => api.createDocumentReminder(docId, data),
        getDocuments: (filters) => api.getDocuments(filters),
      }}
    />
  );
}