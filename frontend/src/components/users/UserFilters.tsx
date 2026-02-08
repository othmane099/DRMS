'use client';

import React from 'react';
import { Input, Select } from '@/components/ui';
import {Role} from '@/types';

interface UserFiltersProps {
  search: string;
  onSearchChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  roleId: string;
  onRoleChange: (value: string) => void;
  status: string;
  onStatusChange: (value: string) => void;
  roles: Role[];
}

export function UserFilters({
  search,
  onSearchChange,
  roleId,
  onRoleChange,
  status,
  onStatusChange,
  roles,
}: UserFiltersProps) {
  return (
    <div className="flex flex-wrap gap-4 mb-6">
      <div className="flex-1 min-w-[200px]">
        <Input
          placeholder="Search by name, username, or email..."
          value={search}
          onChange={onSearchChange}
        />
      </div>
      <div className="w-48">
        <Select
          value={roleId}
          onChange={(e) => onRoleChange(e.target.value)}
          options={[
            { value: '', label: 'All Roles' },
            ...(roles || []).map((role) => ({ value: role.id, label: role.name })),
          ]}
        />
      </div>
      <div className="w-40">
        <Select
          value={status}
          onChange={(e) => onStatusChange(e.target.value)}
          options={[
            { value: '', label: 'All Status' },
            { value: 'active', label: 'Active' },
            { value: 'inactive', label: 'Inactive' },
          ]}
        />
      </div>
    </div>
  );
}
