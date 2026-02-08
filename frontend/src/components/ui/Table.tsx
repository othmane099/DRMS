'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  sortable?: boolean;
  className?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string | number;
  onRowClick?: (item: T) => void;
  selectedIds?: (string | number)[];
  onSelectChange?: (ids: (string | number)[]) => void;
  sortColumn?: string;
  sortDirection?: 'asc' | 'desc';
  onSort?: (column: string) => void;
  emptyMessage?: string;
}

export function Table<T extends object>({
  columns,
  data,
  keyExtractor,
  onRowClick,
  selectedIds,
  onSelectChange,
  sortColumn,
  sortDirection,
  onSort,
  emptyMessage = 'No data found',
}: TableProps<T>) {
  const showSelection = onSelectChange !== undefined;
  const safeData = Array.isArray(data) ? data : [];

  const handleSelectAll = () => {
    if (!onSelectChange) return;
    if (selectedIds?.length === safeData.length) {
      onSelectChange([]);
    } else {
      onSelectChange(safeData.map(keyExtractor));
    }
  };

  const handleSelectRow = (id: string | number) => {
    if (!onSelectChange || !selectedIds) return;
    if (selectedIds.includes(id)) {
      onSelectChange(selectedIds.filter((i) => i !== id));
    } else {
      onSelectChange([...selectedIds, id]);
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-200">
            {showSelection && (
              <th className="px-4 py-3 text-left">
                <input
                  type="checkbox"
                  checked={selectedIds?.length === safeData.length && safeData.length > 0}
                  onChange={handleSelectAll}
                  className="h-4 w-4 rounded border-gray-300 text-black focus:ring-black"
                />
              </th>
            )}
            {columns.map((column) => (
              <th
                key={column.key}
                className={cn(
                  'px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider',
                  column.sortable && 'cursor-pointer hover:text-gray-700',
                  column.className
                )}
                onClick={() => column.sortable && onSort?.(column.key)}
              >
                <div className="flex items-center gap-1">
                  {column.header}
                  {column.sortable && sortColumn === column.key && (
                    <svg
                      className={cn(
                        'w-4 h-4 transition-transform',
                        sortDirection === 'desc' && 'rotate-180'
                      )}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 15l7-7 7 7"
                      />
                    </svg>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {safeData.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length + (showSelection ? 1 : 0)}
                className="px-4 py-8 text-center text-gray-500"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            safeData.map((item) => {
              const id = keyExtractor(item);
              const isSelected = selectedIds?.includes(id);

              return (
                <tr
                  key={id}
                  className={cn(
                    'hover:bg-gray-50 transition-colors',
                    onRowClick && 'cursor-pointer',
                    isSelected && 'bg-gray-50'
                  )}
                  onClick={() => onRowClick?.(item)}
                >
                  {showSelection && (
                    <td className="px-4 py-4" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleSelectRow(id)}
                        className="h-4 w-4 rounded border-gray-300 text-black focus:ring-black"
                      />
                    </td>
                  )}
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={cn('px-4 py-4 text-sm', column.className)}
                    >
                      {column.render
                        ? column.render(item)
                        : ((item as Record<string, unknown>)[column.key] as React.ReactNode)}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
