'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { Button, Card, Pagination, LoadingOverlay } from '@/components/ui';
import {
  UserTable,
  UserFilters,
  BulkActionsDropdown,
} from '@/components/users';
import { CanAccess } from '@/components/auth/CanAccess';
import { AccessDenied } from '@/components/auth/AccessDenied';
import { usePermissions } from '@/hooks/usePermissions';
import { api } from '@/lib/api';
import {User, PaginatedResponse, UserFilters as UserFiltersType, Role, ApiError} from '@/types';
import { debounce } from '@/lib/utils';

export default function UsersPage() {
  const { hasAnyPermission } = usePermissions();
  const [users, setUsers] = useState<PaginatedResponse<User> | null>(null);
  const [roles, setRoles] = useState<Role[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [accessDenied, setAccessDenied] = useState(false);

  // Filters
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [roleId, setRoleId] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Check if user has permission to view users
  const canViewUsers = hasAnyPermission(['users.list', 'users.view']);

  const fetchUsers = useCallback(async () => {
    // Check permission before fetching
    if (!canViewUsers) {
      setAccessDenied(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const filters: UserFiltersType = {
        page,
        page_size: pageSize,
      };
      if (search) filters.search = search;
      if (roleId) filters.role_id = roleId;
      if (status) filters.active = status;

      const data = await api.getUsers(filters);
      console.log('Users API response:', data);
      setUsers(data);
    } catch (error) {
      const apiError = error as ApiError;
      // Handle 403 errors gracefully
      if (apiError.status === 403) {
        setAccessDenied(true);
      } else {
        console.error('Failed to fetch users:', error);
      }
    } finally {
      setIsLoading(false);
    }
  }, [page, search, roleId, status, canViewUsers]);

  const fetchRoles = async () => {
    // Only fetch roles if user has permission to view them
    if (!hasAnyPermission(['roles.list', 'roles.view'])) {
      return;
    }

    try {
      const data = await api.getRoles();
      console.log('Roles API response:', data);
      setRoles(Array.isArray(data) ? data : []);
    } catch (error) {
      const apiError = error as ApiError;
      // Silently handle 403 errors (user lacks permission)
      if (apiError.status !== 403) {
        console.error('Failed to fetch roles:', error);
      }
    }
  };

  useEffect(() => {
    fetchRoles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

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

  const handleRoleChange = (value: string) => {
    setRoleId(value);
    setPage(1);
  };

  const handleStatusChange = (value: string) => {
    setStatus(value);
    setPage(1);
  };

  const handleBulkActionComplete = () => {
    setSelectedIds([]);
    fetchUsers();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Users</h1>
          <p className="text-gray-500">Manage staff members and their permissions</p>
        </div>
        <CanAccess permission="users.create">
          <Link href="/users/new">
            <Button>
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
                  d="M12 4v16m8-8H4"
                />
              </svg>
              Add User
            </Button>
          </Link>
        </CanAccess>
      </div>

      <Card padding="none">
        {accessDenied ? (
          <AccessDenied resource="users" />
        ) : (
          <>
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between gap-4">
                <div className="flex-1">
                  <UserFilters
                    search={searchInput}
                    onSearchChange={handleSearchChange}
                    roleId={roleId}
                    onRoleChange={handleRoleChange}
                    status={status}
                    onStatusChange={handleStatusChange}
                    roles={roles}
                  />
                </div>
                <CanAccess permission="users.update">
                  <BulkActionsDropdown
                    selectedIds={selectedIds}
                    roles={roles}
                    onActionComplete={handleBulkActionComplete}
                  />
                </CanAccess>
              </div>
            </div>

            {isLoading ? (
              <LoadingOverlay message="Loading users..." />
            ) : users && users.data ? (
              <>
                <UserTable
                  users={users.data}
                  selectedIds={selectedIds}
                  onSelectChange={setSelectedIds}
                />
                <Pagination
                  currentPage={users.page}
                  totalPages={users.total_pages || Math.ceil(users.total / pageSize)}
                  onPageChange={setPage}
                />
              </>
            ) : (
              <div className="py-12 text-center text-gray-500">
                Failed to load users
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
