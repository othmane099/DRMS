'use client';

import React from 'react';
import { Table } from '@/components/ui';
import { CanAccess } from '@/components/auth/CanAccess';
import { Subcategory } from '@/types';
import { formatDateTime } from '@/lib/utils';

interface SubcategoryTableProps {
  subcategories: Subcategory[];
  onEdit: (subcategory: Subcategory) => void;
  onDelete: (subcategory: Subcategory) => void;
}

export function SubcategoryTable({ subcategories, onEdit, onDelete }: SubcategoryTableProps) {
  const columns = [
    {
      key: 'title',
      header: 'Subcategory Name',
      render: (subcategory: Subcategory) => (
        <div className="flex items-center gap-3">
          <span className="font-medium">{subcategory.title}</span>
        </div>
      ),
    },
    {
      key: 'category_title',
      header: 'Category',
      render: (subcategory: Subcategory) => (
        <div className="flex items-center">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
            {subcategory.category_title || '-'}
          </span>
        </div>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (subcategory: Subcategory) => (
        <span className="text-gray-500">
          {subcategory.created_at ? formatDateTime(subcategory.created_at) : '-'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (subcategory: Subcategory) => (
        <div className="flex items-center gap-2">
          <CanAccess permission="subcategories.update">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEdit(subcategory);
              }}
              className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
              title="Edit subcategory"
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
          <CanAccess permission="subcategories.delete">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(subcategory);
              }}
              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
              title="Delete subcategory"
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
      data={subcategories}
      keyExtractor={(subcategory) => subcategory.id}
    />
  );
}