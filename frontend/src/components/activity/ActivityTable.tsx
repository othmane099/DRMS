'use client';

import React from 'react';
import { Table, Badge } from '@/components/ui';
import { LoggedHistory } from '@/types';
import { formatDateTime, snakeToTitle } from '@/lib/utils';

interface ActivityTableProps {
  activities: LoggedHistory[];
}

export function ActivityTable({ activities }: ActivityTableProps) {
  const getActionBadgeVariant = (type: string) => {
    const typeLower = type.toLowerCase();
    if (typeLower.includes('failed')) return 'danger';
    if (typeLower.includes('login')) return 'success';
    return 'default';
  };

  const columns = [
    {
      key: 'username',
      header: 'Username',
      render: (activity: LoggedHistory) => (
        <span className="font-medium">
          {activity.details?.username || 'Unknown User'}
        </span>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      render: (activity: LoggedHistory) => (
        <Badge variant={getActionBadgeVariant(activity.type)}>
          {snakeToTitle(activity.type)}
        </Badge>
      ),
    },
    {
      key: 'reason',
      header: 'Reason',
      render: (activity: LoggedHistory) => (
        <span className="text-gray-600 text-sm">
          {activity.details?.reason || '-'}
        </span>
      ),
    },
    {
      key: 'ip',
      header: 'IP Address',
      render: (activity: LoggedHistory) => (
        <span className="text-gray-500 font-mono text-sm">
          {activity.ip || '-'}
        </span>
      ),
    },
    {
      key: 'date',
      header: 'Date',
      render: (activity: LoggedHistory) => (
        <span className="text-gray-500">
          {activity.date ? formatDateTime(activity.date) : formatDateTime(activity.created_at)}
        </span>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      data={activities}
      keyExtractor={(activity) => activity.id}
      emptyMessage="No activity found"
    />
  );
}
