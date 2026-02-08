'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Card, Pagination, LoadingOverlay, Toast, Input } from '@/components/ui';
import { AccessDenied } from '@/components/auth/AccessDenied';
import { usePermissions } from '@/hooks/usePermissions';
import { api } from '@/lib/api';
import {
  PaginatedDocumentHistoryResponse,
  DocumentHistoryFilters as DocumentHistoryFiltersType,
  ApiError,
} from '@/types';
import { debounce } from '@/lib/utils';
import { formatDateTime } from '@/lib/utils';

interface HistoriesListProps {
  title: string;
  description: string;
  permission: string;
  getHistories: typeof api.getDocumentHistories | typeof api.getMyDocumentHistories;
}

export function HistoriesList({ title, description, permission, getHistories }: HistoriesListProps) {
  const { hasAnyPermission } = usePermissions();
  const [histories, setHistories] = useState<PaginatedDocumentHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [accessDenied, setAccessDenied] = useState(false);

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

  // Filters
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Check if user has permission to view document histories
  const canViewHistories = hasAnyPermission([permission]);

  const fetchHistories = useCallback(async () => {
    // Check permission before fetching
    if (!canViewHistories) {
      setAccessDenied(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const filters: DocumentHistoryFiltersType = {
        page,
        page_size: pageSize,
      };
      if (search) filters.search = search;

      const data = await getHistories(filters);
      console.log('Document Histories API response:', data);
      setHistories(data);
    } catch (error) {
      const apiError = error as ApiError;
      // Handle 403 errors gracefully
      if (apiError.status === 403) {
        setAccessDenied(true);
      } else {
        console.error('Failed to fetch document histories:', error);
        showToast(apiError.detail || 'Failed to load document histories', 'error');
      }
    } finally {
      setIsLoading(false);
    }
  }, [page, search, canViewHistories]);

  useEffect(() => {
    fetchHistories();
  }, [fetchHistories]);

  // Debounced search
  const debouncedSearch = useCallback(
    debounce((value: string) => {
      setSearch(value);
      setPage(1);
    }, 300),
    []
  );

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchInput(value);
    debouncedSearch(value);
  };

  const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
    setToast({ message, type, isVisible: true });
  };

  const hideToast = () => {
    setToast((prev) => ({ ...prev, isVisible: false }));
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{title}</h1>
          <p className="text-gray-500">{description}</p>
        </div>
      </div>

      <Card padding="none">
        {accessDenied ? (
          <AccessDenied resource="document histories" />
        ) : (
          <>
            <div className="p-4 border-b border-gray-200">
              <div className="flex gap-4">
                <div className="flex-1">
                  <Input
                    type="text"
                    placeholder="Search by action or description..."
                    value={searchInput}
                    onChange={handleSearchChange}
                  />
                </div>
              </div>
            </div>

            {isLoading ? (
              <LoadingOverlay message="Loading document histories..." />
            ) : histories && histories.data && histories.data.length > 0 ? (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Document
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Action
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Description
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          User
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Date
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {histories.data.map((history) => (
                        <tr key={history.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900">
                              {history.document?.name || 'N/A'}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                              {history.action}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-900 max-w-md">
                              {history.description}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm text-gray-900">
                              {history.creator.username}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm text-gray-900">
                              {formatDateTime(history.created_at)}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <Pagination
                  currentPage={histories.current_page}
                  totalPages={histories.total_pages}
                  onPageChange={setPage}
                />
              </>
            ) : (
              <div className="py-12 text-center text-gray-500">
                No document history found
              </div>
            )}
          </>
        )}
      </Card>

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