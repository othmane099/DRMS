'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Button, Card, Pagination, LoadingOverlay, Modal, Toast } from '@/components/ui';
import { CategoryTable, CategoryFilters, CategoryModal } from '@/components/categories';
import { CanAccess } from '@/components/auth/CanAccess';
import { AccessDenied } from '@/components/auth/AccessDenied';
import { usePermissions } from '@/hooks/usePermissions';
import { api } from '@/lib/api';
import { Category, PaginatedResponse, CategoryFilters as CategoryFiltersType, ApiError } from '@/types';
import { debounce } from '@/lib/utils';

export default function CategoriesPage() {
  const { hasAnyPermission } = usePermissions();
  const [categories, setCategories] = useState<PaginatedResponse<Category> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [accessDenied, setAccessDenied] = useState(false);

  // Modal states
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<Category | undefined>(undefined);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [categoryToDelete, setCategoryToDelete] = useState<Category | null>(null);
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

  // Check if user has permission to view categories
  const canViewCategories = hasAnyPermission(['categories.list']);

  const fetchCategories = useCallback(async () => {
    // Check permission before fetching
    if (!canViewCategories) {
      setAccessDenied(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const filters: CategoryFiltersType = {
        page,
        page_size: pageSize,
      };
      if (search) filters.search = search;

      const data = await api.getCategories(filters);
      console.log('Categories API response:', data);
      setCategories(data);
    } catch (error) {
      const apiError = error as ApiError;
      // Handle 403 errors gracefully
      if (apiError.status === 403) {
        setAccessDenied(true);
      } else {
        console.error('Failed to fetch categories:', error);
      }
    } finally {
      setIsLoading(false);
    }
  }, [page, search, canViewCategories]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

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

  const handleCreateCategory = () => {
    setSelectedCategory(undefined);
    setShowCategoryModal(true);
  };

  const handleEditCategory = (category: Category) => {
    setSelectedCategory(category);
    setShowCategoryModal(true);
  };

  const handleDeleteCategory = (category: Category) => {
    setCategoryToDelete(category);
    setShowDeleteModal(true);
  };

  const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
    setToast({ message, type, isVisible: true });
  };

  const hideToast = () => {
    setToast((prev) => ({ ...prev, isVisible: false }));
  };

  const confirmDelete = async () => {
    if (!categoryToDelete) return;

    setIsDeleting(true);
    try {
      await api.deleteCategory(categoryToDelete.id);
      setShowDeleteModal(false);
      setCategoryToDelete(null);
      showToast('Category deleted successfully', 'success');
      fetchCategories();
    } catch (error) {
      const apiError = error as ApiError;
      console.error('Failed to delete category:', error);
      showToast(apiError.detail || 'Failed to delete category', 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCategorySuccess = () => {
    const message = selectedCategory ? 'Category updated successfully' : 'Category created successfully';
    showToast(message, 'success');
    fetchCategories();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Categories</h1>
          <p className="text-gray-500">Manage document categories and subcategories</p>
        </div>
        <CanAccess permission="categories.create">
          <Button onClick={handleCreateCategory}>
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
            Add Category
          </Button>
        </CanAccess>
      </div>

      <Card padding="none">
        {accessDenied ? (
          <AccessDenied resource="categories" />
        ) : (
          <>
            <div className="p-4 border-b border-gray-200">
              <CategoryFilters
                search={searchInput}
                onSearchChange={handleSearchChange}
              />
            </div>

            {isLoading ? (
              <LoadingOverlay message="Loading categories..." />
            ) : categories && categories.data ? (
              <>
                <CategoryTable
                  categories={categories.data}
                  onEdit={handleEditCategory}
                  onDelete={handleDeleteCategory}
                />
                <Pagination
                  currentPage={categories.page}
                  totalPages={categories.total_pages || Math.ceil(categories.total / pageSize)}
                  onPageChange={setPage}
                />
              </>
            ) : (
              <div className="py-12 text-center text-gray-500">
                Failed to load categories
              </div>
            )}
          </>
        )}
      </Card>

      {/* Create/Edit Category Modal */}
      <CategoryModal
        isOpen={showCategoryModal}
        onClose={() => setShowCategoryModal(false)}
        category={selectedCategory}
        onSuccess={handleCategorySuccess}
      />

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Category"
      >
        {categoryToDelete && (
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
                  Are you sure you want to delete this category?
                </h3>
                <p className="text-gray-600">
                  You are about to delete the category <strong className="text-gray-900">{categoryToDelete.title}</strong>.
                  This action cannot be undone and may affect associated subcategories.
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
                Delete Category
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