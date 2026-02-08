'use client';

import React from 'react';
import { Input, Select } from '@/components/ui';
import { User } from '@/types';

interface ActivityFiltersProps {
  userId: string;
  onUserChange: (value: string) => void;
  type: string;
  onTypeChange: (value: string) => void;
  startDate: string;
  onStartDateChange: (value: string) => void;
  endDate: string;
  onEndDateChange: (value: string) => void;
  users: User[];
}

const TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'login', label: 'Login' },
  { value: 'failed_login', label: 'Failed Login' }
];

export function ActivityFilters({
  userId,
  onUserChange,
  type,
  onTypeChange,
  startDate,
  onStartDateChange,
  endDate,
  onEndDateChange,
  users,
}: ActivityFiltersProps) {
  return (
    <div className="flex flex-wrap gap-4 mb-6">
      <div className="w-48">
        <Select
          value={userId}
          onChange={(e) => onUserChange(e.target.value)}
          options={[
            { value: '', label: 'All Users' },
            ...users.map((user) => ({
              value: user.id,
              label: `${user.first_name} ${user.last_name}`,
            })),
          ]}
        />
      </div>
      <div className="w-40">
        <Select
          value={type}
          onChange={(e) => onTypeChange(e.target.value)}
          options={TYPE_OPTIONS}
        />
      </div>
      <div className="w-40">
        <Input
          type="date"
          value={startDate}
          onChange={(e) => onStartDateChange(e.target.value)}
          placeholder="Start date"
        />
      </div>
      <div className="w-40">
        <Input
          type="date"
          value={endDate}
          onChange={(e) => onEndDateChange(e.target.value)}
          placeholder="End date"
        />
      </div>
    </div>
  );
}
