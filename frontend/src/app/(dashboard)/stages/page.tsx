'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Button, Card, Pagination, LoadingOverlay, Modal, Toast } from '@/components/ui';
import { StageTable, StageFilters, StageModal } from '@/components/stages';
import { CanAccess } from '@/components/auth/CanAccess';
import { AccessDenied } from '@/components/auth/AccessDenied';
import { usePermissions } from '@/hooks/usePermissions';
import { api } from '@/lib/api';
import { Stage, PaginatedResponse, StageFilters as StageFiltersType, ApiError } from '@/types';
import { debounce } from '@/lib/utils';

export default function StagesPage() {
  const { hasAnyPermission } = usePermissions();
  const [stages, setStages] = useState<PaginatedResponse<Stage> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [accessDenied, setAccessDenied] = useState(false);

  // Modal states
  const [showStageModal, setShowStageModal] = useState(false);
  const [selectedStage, setSelectedStage] = useState<Stage | undefined>(undefined);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [stageToDelete, setStageToDelete] = useState<Stage | null>(null);
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

  // Check if user has permission to view stages
  const canViewStages = hasAnyPermission(['stages.list']);

  const fetchStages = useCallback(async () => {
    // Check permission before fetching
    if (!canViewStages) {
      setAccessDenied(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const filters: StageFiltersType = {
        page,
        page_size: pageSize,
      };
      if (search) filters.search = search;

      const data = await api.getStages(filters);
      console.log('Stages API response:', data);
      setStages(data);
    } catch (error) {
      const apiError = error as ApiError;
      // Handle 403 errors gracefully
      if (apiError.status === 403) {
        setAccessDenied(true);
      } else {
        console.error('Failed to fetch stages:', error);
      }
    } finally {
      setIsLoading(false);
    }
  }, [page, search, canViewStages]);

  useEffect(() => {
    fetchStages();
  }, [fetchStages]);

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

  const handleCreateStage = () => {
    setSelectedStage(undefined);
    setShowStageModal(true);
  };

  const handleEditStage = (stage: Stage) => {
    setSelectedStage(stage);
    setShowStageModal(true);
  };

  const handleDeleteStage = (stage: Stage) => {
    setStageToDelete(stage);
    setShowDeleteModal(true);
  };

  const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
    setToast({ message, type, isVisible: true });
  };

  const hideToast = () => {
    setToast((prev) => ({ ...prev, isVisible: false }));
  };

  const confirmDelete = async () => {
    if (!stageToDelete) return;

    setIsDeleting(true);
    try {
      await api.deleteStage(stageToDelete.id);
      setShowDeleteModal(false);
      setStageToDelete(null);
      showToast('Stage deleted successfully', 'success');
      fetchStages();
    } catch (error) {
      const apiError = error as ApiError;
      console.error('Failed to delete stage:', error);
      showToast(apiError.detail || 'Failed to delete stage', 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleStageSuccess = () => {
    const message = selectedStage ? 'Stage updated successfully' : 'Stage created successfully';
    showToast(message, 'success');
    fetchStages();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Stages</h1>
          <p className="text-gray-500">Manage workflow stages for documents</p>
        </div>
        <CanAccess permission="stages.create">
          <Button onClick={handleCreateStage}>
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
            Add Stage
          </Button>
        </CanAccess>
      </div>

      <Card padding="none">
        {accessDenied ? (
          <AccessDenied resource="stages" />
        ) : (
          <>
            <div className="p-4 border-b border-gray-200">
              <StageFilters
                search={searchInput}
                onSearchChange={handleSearchChange}
              />
            </div>

            {isLoading ? (
              <LoadingOverlay message="Loading stages..." />
            ) : stages && stages.data ? (
              <>
                <StageTable
                  stages={stages.data}
                  onEdit={handleEditStage}
                  onDelete={handleDeleteStage}
                />
                <Pagination
                  currentPage={stages.page}
                  totalPages={stages.total_pages || Math.ceil(stages.total / pageSize)}
                  onPageChange={setPage}
                />
              </>
            ) : (
              <div className="py-12 text-center text-gray-500">
                Failed to load stages
              </div>
            )}
          </>
        )}
      </Card>

      {/* Create/Edit Stage Modal */}
      <StageModal
        isOpen={showStageModal}
        onClose={() => setShowStageModal(false)}
        stage={selectedStage}
        onSuccess={handleStageSuccess}
      />

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Stage"
      >
        {stageToDelete && (
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
                  Are you sure you want to delete this stage?
                </h3>
                <p className="text-gray-600">
                  You are about to delete the stage <strong className="text-gray-900">{stageToDelete.title}</strong>.
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
                Delete Stage
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