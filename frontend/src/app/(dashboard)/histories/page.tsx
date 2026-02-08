'use client';

import { HistoriesList } from '@/components/histories';
import { api } from '@/lib/api';

export default function HistoriesPage() {
  return (
    <HistoriesList
      title="Document History"
      description="View all document actions and changes"
      permission="documents.history"
      getHistories={(filters) => api.getDocumentHistories(filters)}
    />
  );
}