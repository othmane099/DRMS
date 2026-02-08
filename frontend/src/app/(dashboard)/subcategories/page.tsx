'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Button, Card, Pagination, LoadingOverlay, Modal, Toast } from '@/components/ui';
import { SubcategoryTable, SubcategoryFilters, SubcategoryModal } from '@/components/subcategories';
import { CanAccess } from '@/components/auth/CanAccess';
import { AccessDenied } from '@/components/auth/AccessDenied';
import { usePermissions } from '@/hooks/usePermissions';
import { api } from '@/lib/api';
import { Subcategory, Category, PaginatedResponse, SubcategoryFilters as SubcategoryFiltersType, ApiError } from '@/types';
import { debounce } from '@/lib/utils';

export default function SubcategoriesPage() {
  const { hasAnyPermission } = usePermissions();
  const [subcategories, setSubcategories] = useState<PaginatedResponse<Subcategory> | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [accessDenied, setAccessDenied] = useState(false);

  // Modal states
  const [showSubcategoryModal, setShowSubcategoryModal] = useState(false);
  const [selectedSubcategory, setSelectedSubcategory] = useState<Subcategory | undefined>(undefined);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [subcategoryToDelete, setSubcategoryToDelete] = useState<Subcategory | null>(null);
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
  const [categoryId, setCategoryId] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Check if user has permission to view subcategories
  const canViewSubcategories = hasAnyPermission(['subcategories.list']);

  // Fetch categories for filter
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const data = await api.getCategories({ page: 1, page_size: 1000 });
        setCategories(data.data || []);
      } catch (error) {
        console.error('Failed to fetch categories:', error);
      }
    };
    fetchCategories();
  }, []);

  const fetchSubcategories = useCallback(async () => {
    // Check permission before fetching
    if (!canViewSubcategories) {
      setAccessDenied(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const filters: SubcategoryFiltersType = {
        page,
        page_size: pageSize,
      };
      if (search) filters.search = search;
      if (categoryId) filters.category_id = categoryId;

      const data = await api.getSubcategories(filters);
      console.log('Subcategories API response:', data);
      setSubcategories(data);
    } catch (error) {
      const apiError = error as ApiError;
      // Handle 403 errors gracefully
      if (apiError.status === 403) {
        setAccessDenied(true);
      } else {
        console.error('Failed to fetch subcategories:', error);
      }
    } finally {
      setIsLoading(false);
    }
  }, [page, search, categoryId, canViewSubcategories]);

  useEffect(() => {
    fetchSubcategories();
  }, [fetchSubcategories]);

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

  const handleCategoryChange = (value: string) => {
    setCategoryId(value);
    setPage(1);
  };

  const handleCreateSubcategory = () => {
    setSelectedSubcategory(undefined);
    setShowSubcategoryModal(true);
  };

  const handleEditSubcategory = (subcategory: Subcategory) => {
    setSelectedSubcategory(subcategory);
    setShowSubcategoryModal(true);
  };

  const handleDeleteSubcategory = (subcategory: Subcategory) => {
    setSubcategoryToDelete(subcategory);
    setShowDeleteModal(true);
  };

  const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
    setToast({ message, type, isVisible: true });
  };

  const hideToast = () => {
    setToast((prev) => ({ ...prev, isVisible: false }));
  };

  const confirmDelete = async () => {
    if (!subcategoryToDelete) return;

    setIsDeleting(true);
    try {
      await api.deleteSubcategory(subcategoryToDelete.id);
      setShowDeleteModal(false);
      setSubcategoryToDelete(null);
      showToast('Subcategory deleted successfully', 'success');
      fetchSubcategories();
    } catch (error) {
      const apiError = error as ApiError;
      console.error('Failed to delete subcategory:', error);
      showToast(apiError.detail || 'Failed to delete subcategory', 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleSubcategorySuccess = () => {
    const message = selectedSubcategory ? 'Subcategory updated successfully' : 'Subcategory created successfully';
    showToast(message, 'success');
    fetchSubcategories();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Subcategories</h1>
          <p className="text-gray-500">Manage subcategories within each category</p>
        </div>
        <CanAccess permission="subcategories.create">
          <Button onClick={handleCreateSubcategory}>
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
            Add Subcategory
          </Button>
        </CanAccess>
      </div>

      <Card padding="none">
        {accessDenied ? (
          <AccessDenied resource="subcategories" />
        ) : (
          <>
            <div className="p-4 border-b border-gray-200">
              <SubcategoryFilters
                search={searchInput}
                categoryId={categoryId}
                categories={categories}
                onSearchChange={handleSearchChange}
                onCategoryChange={handleCategoryChange}
              />
            </div>

            {isLoading ? (
              <LoadingOverlay message="Loading subcategories..." />
            ) : subcategories && subcategories.data ? (
              <>
                <SubcategoryTable
                  subcategories={subcategories.data}
                  onEdit={handleEditSubcategory}
                  onDelete={handleDeleteSubcategory}
                />
                <Pagination
                  currentPage={subcategories.page}
                  totalPages={subcategories.total_pages || Math.ceil(subcategories.total / pageSize)}
                  onPageChange={setPage}
                />
              </>
            ) : (
              <div className="py-12 text-center text-gray-500">
                Failed to load subcategories
              </div>
            )}
          </>
        )}
      </Card>

      {/* Create/Edit Subcategory Modal */}
      <SubcategoryModal
        isOpen={showSubcategoryModal}
        onClose={() => setShowSubcategoryModal(false)}
        subcategory={selectedSubcategory}
        categories={categories}
        onSuccess={handleSubcategorySuccess}
      />

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Subcategory"
      >
        {subcategoryToDelete && (
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
                  Are you sure you want to delete this subcategory?
                </h3>
                <p className="text-gray-600">
                  You are about to delete the subcategory <strong className="text-gray-900">{subcategoryToDelete.title}</strong>.
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
                Delete Subcategory
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