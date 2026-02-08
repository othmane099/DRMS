'use client';

import React from 'react';
import { Table } from '@/components/ui';
import { CanAccess } from '@/components/auth/CanAccess';
import { Tag } from '@/types';
import { formatDateTime } from '@/lib/utils';

interface TagTableProps {
  tags: Tag[];
  onEdit: (tag: Tag) => void;
  onDelete: (tag: Tag) => void;
}

export function TagTable({ tags, onEdit, onDelete }: TagTableProps) {
  const columns = [
    {
      key: 'title',
      header: 'Tag Name',
      render: (tag: Tag) => (
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
            {tag.title}
          </span>
        </div>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (tag: Tag) => (
        <span className="text-gray-500">
          {tag.created_at ? formatDateTime(tag.created_at) : '-'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (tag: Tag) => (
        <div className="flex items-center gap-2">
          <CanAccess permission="tags.update">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEdit(tag);
              }}
              className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
              title="Edit tag"
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
          <CanAccess permission="tags.delete">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(tag);
              }}
              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
              title="Delete tag"
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
      data={tags}
      keyExtractor={(tag) => tag.id}
    />
  );
}
