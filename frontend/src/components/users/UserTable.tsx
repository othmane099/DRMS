'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Table, Badge } from '@/components/ui';
import { User } from '@/types';
import { formatDate, getInitials } from '@/lib/utils';

interface UserTableProps {
  users: User[];
  selectedIds: string[];
  onSelectChange: (ids: string[]) => void;
}

export function UserTable({ users, selectedIds, onSelectChange }: UserTableProps) {
  const router = useRouter();

  const columns = [
    {
      key: 'user',
      header: 'User',
      render: (user: User) => (
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center text-sm font-medium">
            {getInitials(user.first_name, user.last_name)}
          </div>
          <div>
            <p className="font-medium">
              {user.first_name} {user.last_name}
            </p>
            <p className="text-sm text-gray-500">@{user.username}</p>
          </div>
        </div>
      ),
    },
    {
      key: 'email',
      header: 'Email',
      render: (user: User) => (
        <span className="text-gray-600">{user.email || '-'}</span>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      render: (user: User) => (
        user.role ? (
          <Badge>{user.role.name}</Badge>
        ) : (
          <span className="text-gray-400">No role</span>
        )
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (user: User) => (
        <Badge variant={user.is_active ? 'success' : 'danger'}>
          {user.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (user: User) => (
        <span className="text-gray-500">
          {user.created_at ? formatDate(user.created_at) : '-'}
        </span>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      data={users}
      keyExtractor={(user) => user.id}
      onRowClick={(user) => router.push(`/users/${user.id}`)}
      selectedIds={selectedIds}
      onSelectChange={(ids) => onSelectChange(ids as string[])}
    />
  );
}
