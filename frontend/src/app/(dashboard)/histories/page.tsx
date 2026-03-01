'use client';

import { HistoriesList } from '@/components/histories';
import { api } from '@/lib/api';

export default function HistoriesPage() {
  return (
    <HistoriesList
      title="Document History"
      description="View document actions and changes"
      permission="documents.history"
      permissionMy="documents.history_my"
      getHistories={(filters) => api.getDocumentHistories(filters)}
    />
  );
}