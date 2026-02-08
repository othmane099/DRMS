'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Table } from '@/components/ui';
import { CanAccess } from '@/components/auth/CanAccess';
import { Category } from '@/types';
import { formatDateTime } from '@/lib/utils';

interface CategoryTableProps {
  categories: Category[];
  onEdit: (category: Category) => void;
  onDelete: (category: Category) => void;
}

export function CategoryTable({ categories, onEdit, onDelete }: CategoryTableProps) {
  const router = useRouter();

  const columns = [
    {
      key: 'title',
      header: 'Category Name',
      render: (category: Category) => (
        <button
          onClick={() => router.push(`/categories/${category.id}`)}
          className="flex items-center gap-3 text-left hover:text-blue-600 transition-colors"
        >
          <span className="font-medium">{category.title}</span>
          <svg
            className="w-4 h-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>
      ),
    },
    {
      key: 'subcategory_count',
      header: 'Subcategories',
      render: (category: Category) => (
        <div className="flex items-center">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            {category.subcategory_count || 0}
          </span>
        </div>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (category: Category) => (
        <span className="text-gray-500">
          {category.created_at ? formatDateTime(category.created_at) : '-'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (category: Category) => (
        <div className="flex items-center gap-2">
          <CanAccess permission="categories.update">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEdit(category);
              }}
              className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
              title="Edit category"
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
          <CanAccess permission="categories.delete">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(category);
              }}
              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
              title="Delete category"
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
      data={categories}
      keyExtractor={(category) => category.id}
    />
  );
}