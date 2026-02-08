'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Table, Badge, Button } from '@/components/ui';
import { CanAccess } from '@/components/auth/CanAccess';
import {Role} from '@/types';
import { formatDate } from '@/lib/utils';

interface RoleTableProps {
  roles: Role[];
  onDelete: (role: Role) => void;
  onStatusToggle?: (role: Role, isActive: boolean) => void;
}

export function RoleTable({ roles, onDelete, onStatusToggle }: RoleTableProps) {
  const router = useRouter();

  const columns = [
    {
      key: 'name',
      header: 'Role',
      render: (role: Role) => (
        <div>
          <p className="font-medium">{role.name}</p>
          {role.description && (
            <p className="text-sm text-gray-500 line-clamp-1">{role.description}</p>
          )}
        </div>
      ),
    },
    {
      key: 'permissions',
      header: 'Permissions',
      render: (role: Role) => {
        const permCount = role.permission_count ;
        return <Badge>{permCount} permissions</Badge>;
      },
    },
    {
      key: 'users',
      header: 'Users',
      render: (role: Role) => (
        <span className="text-gray-600">
          {role.user_count ?? 0} user{(role.user_count ?? 0) !== 1 ? 's' : ''}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (role: Role) => (
        <Badge variant={role.is_active ? 'success' : 'default'}>
          {role.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (role: Role) => (
        <span className="text-gray-500">
          {role.created_at ? formatDate(role.created_at) : '-'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (role: Role) => (
        <div className="flex justify-end gap-1" onClick={(e) => e.stopPropagation()}>
          {onStatusToggle && (
            <CanAccess permission="roles.update">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onStatusToggle(role, !role.is_active)}
                className="p-2"
                title={role.is_active ? 'Deactivate' : 'Activate'}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d={role.is_active
                      ? "M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                      : "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    }
                  />
                </svg>
              </Button>
            </CanAccess>
          )}
          <CanAccess permission="roles.update">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push(`/roles/new?edit=${role.id}`)}
              className="p-2"
              title="Edit"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                />
              </svg>
            </Button>
          </CanAccess>
          <CanAccess permission="roles.delete">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(role)}
              className="p-2 text-red-600 hover:text-red-700 hover:bg-red-50"
              title="Delete"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </Button>
          </CanAccess>
        </div>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      data={roles}
      keyExtractor={(role) => role.id}
      emptyMessage="No roles found"
    />
  );
}
