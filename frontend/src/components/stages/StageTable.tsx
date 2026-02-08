'use client';

import React from 'react';
import { Table } from '@/components/ui';
import { CanAccess } from '@/components/auth/CanAccess';
import { Stage } from '@/types';
import { formatDateTime } from '@/lib/utils';

interface StageTableProps {
  stages: Stage[];
  onEdit: (stage: Stage) => void;
  onDelete: (stage: Stage) => void;
}

export function StageTable({ stages, onEdit, onDelete }: StageTableProps) {
  const columns = [
    {
      key: 'title',
      header: 'Stage Name',
      render: (stage: Stage) => (
        <div className="flex items-center gap-3">
          <span className="font-medium">{stage.title}</span>
        </div>
      ),
    },
    {
      key: 'color',
      header: 'Color',
      render: (stage: Stage) => (
        <div className="flex items-center gap-2">
          {stage.color ? (
            <>
              <div
                className="w-6 h-6 rounded border border-gray-300"
                style={{ backgroundColor: stage.color }}
              />
              <span className="text-sm text-gray-600 font-mono">{stage.color}</span>
            </>
          ) : (
            <span className="text-gray-400">No color</span>
          )}
        </div>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (stage: Stage) => (
        <span className="text-gray-500">
          {stage.created_at ? formatDateTime(stage.created_at) : '-'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (stage: Stage) => (
        <div className="flex items-center gap-2">
          <CanAccess permission="stages.update">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEdit(stage);
              }}
              className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
              title="Edit stage"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                />
              </svg>
            </button>
          </CanAccess>
          <CanAccess permission="stages.delete">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(stage);
              }}
              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
              title="Delete stage"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          </CanAccess>
        </div>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      data={stages}
      keyExtractor={(stage) => stage.id}
    />
  );
}