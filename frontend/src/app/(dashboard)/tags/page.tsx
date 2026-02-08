'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Button, Card, Pagination, LoadingOverlay, Modal, Toast } from '@/components/ui';
import { TagTable, TagFilters, TagModal } from '@/components/tags';
import { CanAccess } from '@/components/auth/CanAccess';
import { AccessDenied } from '@/components/auth/AccessDenied';
import { usePermissions } from '@/hooks/usePermissions';
import { api } from '@/lib/api';
import { Tag, PaginatedResponse, TagFilters as TagFiltersType, ApiError } from '@/types';
import { debounce } from '@/lib/utils';

export default function TagsPage() {
  const { hasAnyPermission } = usePermissions();
  const [tags, setTags] = useState<PaginatedResponse<Tag> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [accessDenied, setAccessDenied] = useState(false);

  // Modal states
  const [showTagModal, setShowTagModal] = useState(false);
  const [selectedTag, setSelectedTag] = useState<Tag | undefined>(undefined);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [tagToDelete, setTagToDelete] = useState<Tag | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Toast notification state
  const [toast, setToast] = useState<{
    message: string;
    type: 'success' | 'error' | 'info' | 'warning';
    isVisible: boolean;
  }>({
    message: '',
    type: 'success',
    isVisible: false,
  });

  // Filters
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Check if user has permission to view tags
  const canViewTags = hasAnyPermission(['tags.list']);

  const fetchTags = useCallback(async () => {
    // Check permission before fetching
    if (!canViewTags) {
      setAccessDenied(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const filters: TagFiltersType = {
        page,
        page_size: pageSize,
      };
      if (search) filters.search = search;

      const data = await api.getTags(filters);
      console.log('Tags API response:', data);
      setTags(data);
    } catch (error) {
      const apiError = error as ApiError;
      // Handle 403 errors gracefully
      if (apiError.status === 403) {
        setAccessDenied(true);
      } else {
        console.error('Failed to fetch tags:', error);
      }
    } finally {
      setIsLoading(false);
    }
  }, [page, search, canViewTags]);

  useEffect(() => {
    fetchTags();
  }, [fetchTags]);

  // Debounced search
  const debouncedSearch = useCallback(
    debounce((value: string) => {
      setSearch(value);
      setPage(1);
    }, 300),
    []
  );

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchInput(value);
    debouncedSearch(value);
  };

  const handleCreateTag = () => {
    setSelectedTag(undefined);
    setShowTagModal(true);
  };

  const handleEditTag = (tag: Tag) => {
    setSelectedTag(tag);
    setShowTagModal(true);
  };

  const handleDeleteTag = (tag: Tag) => {
    setTagToDelete(tag);
    setShowDeleteModal(true);
  };

  const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
    setToast({ message, type, isVisible: true });
  };

  const hideToast = () => {
    setToast((prev) => ({ ...prev, isVisible: false }));
  };

  const confirmDelete = async () => {
    if (!tagToDelete) return;

    setIsDeleting(true);
    try {
      await api.deleteTag(tagToDelete.id);
      setShowDeleteModal(false);
      setTagToDelete(null);
      showToast('Tag deleted successfully', 'success');
      fetchTags();
    } catch (error) {
      const apiError = error as ApiError;
      console.error('Failed to delete tag:', error);
      showToast(apiError.detail || 'Failed to delete tag', 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleTagSuccess = () => {
    const message = selectedTag ? 'Tag updated successfully' : 'Tag created successfully';
    showToast(message, 'success');
    fetchTags();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Tags</h1>
          <p className="text-gray-500">Manage document tags for categorization</p>
        </div>
        <CanAccess permission="tags.create">
          <Button onClick={handleCreateTag}>
            <svg
              className="w-4 h-4 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
            Add Tag
          </Button>
        </CanAccess>
      </div>

      <Card padding="none">
        {accessDenied ? (
          <AccessDenied resource="tags" />
        ) : (
          <>
            <div className="p-4 border-b border-gray-200">
              <TagFilters
                search={searchInput}
                onSearchChange={handleSearchChange}
              />
            </div>

            {isLoading ? (
              <LoadingOverlay message="Loading tags..." />
            ) : tags && tags.data ? (
              <>
                <TagTable
                  tags={tags.data}
                  onEdit={handleEditTag}
                  onDelete={handleDeleteTag}
                />
                <Pagination
                  currentPage={tags.page}
                  totalPages={tags.total_pages || Math.ceil(tags.total / pageSize)}
                  onPageChange={setPage}
                />
              </>
            ) : (
              <div className="py-12 text-center text-gray-500">
                Failed to load tags
              </div>
            )}
          </>
        )}
      </Card>

      {/* Create/Edit Tag Modal */}
      <TagModal
        isOpen={showTagModal}
        onClose={() => setShowTagModal(false)}
        tag={selectedTag}
        onSuccess={handleTagSuccess}
      />

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Tag"
      >
        {tagToDelete && (
          <>
            <div className="flex items-start gap-3 mb-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <svg
                  className="w-5 h-5 text-red-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Are you sure you want to delete this tag?
                </h3>
                <p className="text-gray-600">
                  You are about to delete the tag <strong className="text-gray-900">{tagToDelete.title}</strong>.
                  This action cannot be undone.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Button
                variant="secondary"
                onClick={() => setShowDeleteModal(false)}
                disabled={isDeleting}
              >
                Cancel
              </Button>
              <Button variant="danger" onClick={confirmDelete} isLoading={isDeleting}>
                Delete Tag
              </Button>
            </div>
          </>
        )}
      </Modal>

      {/* Toast Notification */}
      <Toast
        message={toast.message}
        type={toast.type}
        isVisible={toast.isVisible}
        onClose={hideToast}
      />
    </div>
  );
}