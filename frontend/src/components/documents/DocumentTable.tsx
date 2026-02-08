'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Table, Badge } from '@/components/ui';
import { CanAccess } from '@/components/auth/CanAccess';
import { useAuth } from '@/hooks/useAuth';
import { Document } from '@/types';
import { formatDateTime } from '@/lib/utils';

interface DocumentTableProps {
  documents: Document[];
  onEdit: (document: Document) => void;
  onDelete: (document: Document) => void;
  onArchive: (document: Document) => void;
  onShare: (document: Document) => void;
  editPermission?: string;
  deletePermission?: string;
  sharePermission?: string;
  archivePermission?: string;
  basePath?: string;
}

export function DocumentTable({
  documents,
  onEdit,
  onDelete,
  onArchive,
  onShare,
  editPermission = 'documents.update',
  deletePermission = 'documents.delete',
  sharePermission = 'documents.share',
  archivePermission = 'documents.archive',
  basePath = '/documents',
}: DocumentTableProps) {
  const router = useRouter();
  const { user } = useAuth();

  // Helper function to check if current user is the owner of the document
  const isDocumentOwner = (document: Document) => {
    return user && document.created_by === user.id;
  };
  const columns = [
    {
      key: 'name',
      header: 'Document Name',
      render: (document: Document) => (
        <div>
          <button
            onClick={() => router.push(`${basePath}/${document.id}`)}
            className="flex items-center gap-3 text-left hover:text-blue-600 transition-colors"
          >
            <span className="font-medium">{document.name}</span>
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
        </div>
      ),
    },
    {
      key: 'category',
      header: 'Category',
      render: (document: Document) => (
        <span className="text-gray-700">
          {document.category?.title || '-'}
        </span>
      ),
    },
    {
      key: 'subcategory',
      header: 'Subcategory',
      render: (document: Document) => (
        <span className="text-gray-700">
          {document.subcategory?.title || '-'}
        </span>
      ),
    },
    {
      key: 'stage',
      header: 'Stage',
      render: (document: Document) => (
        <div className="flex items-center">
          {document.stage?.title ? (
            <Badge color={document.stage.color}>{document.stage.title}</Badge>
          ) : (
            <span className="text-gray-400">-</span>
          )}
        </div>
      ),
    },
    {
      key: 'assigned_to',
      header: 'Assigned To',
      render: (document: Document) => (
        <span className="text-gray-700">
          {document.assigned_user?.username || '-'}
        </span>
      ),
    },
    {
      key: 'tags',
      header: 'Tags',
      render: (document: Document) => (
        <div className="flex flex-wrap gap-1">
          {document.tags && document.tags.length > 0 ? (
            document.tags.map((tag) => (
              <span
                key={tag.id}
                className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700"
              >
                {tag.title}
              </span>
            ))
          ) : (
            <span className="text-gray-400">-</span>
          )}
        </div>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (document: Document) => (
        <div className="text-sm">
          <div className="text-gray-500">
            {document.created_at ? formatDateTime(document.created_at) : '-'}
          </div>
          <div className="text-gray-400 text-xs">
            by {document.creator?.username || 'Unknown'}
          </div>
        </div>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (document: Document) => (
        <div className="flex items-center gap-2">
          {isDocumentOwner(document) && (
            <CanAccess permission={editPermission}>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(document);
                }}
                className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                title="Edit document"
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
          )}
          {isDocumentOwner(document) && (
            <CanAccess permission={sharePermission}>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onShare(document);
                }}
                className="p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors"
                title="Generate share link"
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
                    d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
                  />
                </svg>
              </button>
            </CanAccess>
          )}
          {isDocumentOwner(document) && (
            <CanAccess permission={archivePermission}>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onArchive(document);
                }}
                className={`p-1.5 rounded transition-colors ${
                  document.archive
                    ? 'text-gray-400 hover:text-green-600 hover:bg-green-50'
                    : 'text-gray-400 hover:text-yellow-600 hover:bg-yellow-50'
                }`}
                title={document.archive ? 'Unarchive document' : 'Archive document'}
              >
                {document.archive ? (
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
                      d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-5 3l-2 2m0 0l-2-2m2 2V9"
                    />
                  </svg>
                ) : (
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
                      d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                    />
                  </svg>
                )}
              </button>
            </CanAccess>
          )}
          {isDocumentOwner(document) && (
            <CanAccess permission={deletePermission}>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(document);
                }}
                className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                title="Delete document"
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
          )}
        </div>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      data={documents}
      keyExtractor={(document) => document.id}
    />
  );
}