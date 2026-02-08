'use client';

import { HistoriesList } from '@/components/histories';
import { api } from '@/lib/api';

export default function MyHistoriesPage() {
  return (
    <HistoriesList
      title="My Document History"
      description="View your document actions and changes"
      permission="documents.history_my"
      getHistories={(filters) => api.getMyDocumentHistories(filters)}
    />
  );
}