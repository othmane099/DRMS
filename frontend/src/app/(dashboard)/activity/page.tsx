'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Button, Card, Pagination, LoadingOverlay } from '@/components/ui';
import { ActivityTable, ActivityFilters } from '@/components/activity';
import { CanAccess } from '@/components/auth/CanAccess';
import { AccessDenied } from '@/components/auth/AccessDenied';
import { usePermissions } from '@/hooks/usePermissions';
import { api } from '@/lib/api';
import {
  User,
  LoggedHistory,
  PaginatedResponse,
  ActivityFilters as ActivityFiltersType,
  ApiError,
} from '@/types';
import { generateCSV, downloadFile, formatDateTime, snakeToTitle } from '@/lib/utils';

export default function ActivityPage() {
  const { hasAnyPermission, hasPermission } = usePermissions();
  const [activities, setActivities] = useState<PaginatedResponse<LoggedHistory> | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [accessDenied, setAccessDenied] = useState(false);

  // Filters
  const [userId, setUserId] = useState('');
  const [type, setType] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Check if user has permission to view logged history
  const canViewActivity = hasPermission('logged_histories.view');

  const fetchActivities = useCallback(async () => {
    // Check permission before fetching
    if (!canViewActivity) {
      setAccessDenied(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const filters: ActivityFiltersType = {
        page,
        page_size: pageSize,
      };
      if (userId) filters.user_id = userId;
      if (type) filters.type = type;
      if (startDate) filters.date_from = startDate;
      if (endDate) filters.date_to = endDate;

      const data = await api.getActivityLogs(filters);
      setActivities(data);
    } catch (error) {
      const apiError = error as ApiError;
      // Handle 403 errors gracefully
      if (apiError.status === 403) {
        setAccessDenied(true);
      } else {
        console.error('Failed to fetch activities:', error);
      }
    } finally {
      setIsLoading(false);
    }
  }, [page, userId, type, startDate, endDate, canViewActivity]);

  const fetchUsers = async () => {
    // Only fetch users if user has permission to view them
    if (!hasAnyPermission(['users.list', 'users.view'])) {
      return;
    }

    try {
      const data = await api.getUsers({ page_size: 100 });
      setUsers(data.data);
    } catch (error) {
      const apiError = error as ApiError;
      // Silently handle 403 errors (user lacks permission)
      if (apiError.status !== 403) {
        console.error('Failed to fetch users:', error);
      }
    }
  };

  useEffect(() => {
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchActivities();
  }, [fetchActivities]);

  const handleExportCSV = async () => {
    setIsExporting(true);
    try {
      // Fetch all data for export (without pagination)
      const filters: ActivityFiltersType = {
        page: 1,
        page_size: 1000, // Get all records
      };
      if (userId) filters.user_id = userId;
      if (type) filters.type = type;
      if (startDate) filters.date_from = startDate;
      if (endDate) filters.date_to = endDate;

      const data = await api.getActivityLogs(filters);

      const csvData = data.data.map((activity) => ({
        user: activity.user
          ? `${activity.user.first_name} ${activity.user.last_name}`
          : activity.user_name || 'Unknown',
        username: activity.user?.username || '',
        type: snakeToTitle(activity.type),
        ip: activity.ip || '',
        date: activity.date ? formatDateTime(activity.date) : formatDateTime(activity.created_at),
        details: activity.details ? JSON.stringify(activity.details) : '',
      }));

      const csv = generateCSV(csvData, [
        { key: 'user', label: 'User' },
        { key: 'username', label: 'Username' },
        { key: 'type', label: 'Type' },
        { key: 'ip', label: 'IP Address' },
        { key: 'date', label: 'Date' },
        { key: 'details', label: 'Details' },
      ]);

      const filename = `logged_history_${new Date().toISOString().split('T')[0]}.csv`;
      downloadFile(csv, filename, 'text/csv');
    } catch (error) {
      console.error('Failed to export:', error);
    } finally {
      setIsExporting(false);
    }
  };

  const handleFilterChange = (setter: (value: string) => void) => (value: string) => {
    setter(value);
    setPage(1);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Logged History</h1>
          <p className="text-gray-500">Monitor all login and system activity</p>
        </div>
        <CanAccess permission="logged_histories.view">
          <Button
            variant="secondary"
            onClick={handleExportCSV}
            isLoading={isExporting}
          >
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
                d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            Export CSV
          </Button>
        </CanAccess>
      </div>

      <Card padding="none">
        {accessDenied ? (
          <AccessDenied resource="logged history" />
        ) : (
          <>
            <div className="p-4 border-b border-gray-200">
              <ActivityFilters
                userId={userId}
                onUserChange={handleFilterChange(setUserId)}
                type={type}
                onTypeChange={handleFilterChange(setType)}
                startDate={startDate}
                onStartDateChange={handleFilterChange(setStartDate)}
                endDate={endDate}
                onEndDateChange={handleFilterChange(setEndDate)}
                users={users}
              />
            </div>

            {isLoading ? (
              <LoadingOverlay message="Loading logged history..." />
            ) : activities && activities.data ? (
              <>
                <ActivityTable activities={activities.data} />
                <Pagination
                  currentPage={activities.page}
                  totalPages={activities.total_pages || Math.ceil(activities.total / pageSize)}
                  onPageChange={setPage}
                />
              </>
            ) : (
              <div className="py-12 text-center text-gray-500">
                Failed to load logged history
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
