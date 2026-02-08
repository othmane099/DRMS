'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Button, Card, CardHeader, LoadingOverlay } from '@/components/ui';
import { CanAccess } from '@/components/auth/CanAccess';
import { AccessDenied } from '@/components/auth/AccessDenied';
import { usePermissions } from '@/hooks/usePermissions';
import { api } from '@/lib/api';
import { Category, BasicSubcategory, ApiError } from '@/types';
import { formatDateTime } from '@/lib/utils';

export default function CategoryDetailPage() {
  const router = useRouter();
  const params = useParams();
  const categoryId = params.id as string;
  const { hasAnyPermission } = usePermissions();

  const [category, setCategory] = useState<Category | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [accessDenied, setAccessDenied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check if user has permission to view subcategories
  const canViewSubcategories = hasAnyPermission(['subcategories.view']);

  useEffect(() => {
    const fetchCategory = async () => {
      if (!canViewSubcategories) {
        setAccessDenied(true);
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      try {
        const data = await api.getCategory(categoryId);
        setCategory(data);
      } catch (err) {
        const apiError = err as ApiError;
        if (apiError.status === 403) {
          setAccessDenied(true);
        } else {
          setError(apiError.detail || 'Failed to load category');
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchCategory();
  }, [categoryId, canViewSubcategories]);

  if (isLoading) {
    return <LoadingOverlay message="Loading category details..." />;
  }

  if (accessDenied) {
    return <AccessDenied resource="category details" />;
  }

  if (error || !category) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Category Not Found</h2>
          <p className="text-gray-600 mb-6">{error || 'The category you are looking for does not exist.'}</p>
          <Button onClick={() => router.push('/categories')}>
            Back to Categories
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Button
              variant="secondary"
              onClick={() => router.push('/categories')}
              className="p-2"
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
                  d="M10 19l-7-7m0 0l7-7m-7 7h18"
                />
              </svg>
            </Button>
            <h1 className="text-2xl font-bold">{category.title}</h1>
          </div>
          <p className="text-gray-500 ml-14">View category details and subcategories</p>
        </div>
      </div>

      <div className="grid gap-6">
        {/* Category Information */}
        <Card>
          <CardHeader title="Category Information" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category Name
              </label>
              <p className="text-gray-900">{category.title}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Subcategory Count
              </label>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                {category.subcategory_count || 0}
              </span>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Created At
              </label>
              <p className="text-gray-900">
                {category.created_at ? formatDateTime(category.created_at) : '-'}
              </p>
            </div>
            {category.updated_at && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Last Updated
                </label>
                <p className="text-gray-900">
                  {formatDateTime(category.updated_at)}
                </p>
              </div>
            )}
          </div>
        </Card>

        {/* Subcategories List */}
        <Card>
          <div className="flex items-center justify-between mb-6">
            <CardHeader
              title="Subcategories"
              description={`${category.subcategory_count || 0} subcategories in this category`}
            />
            <CanAccess permission="subcategories.list">
              <Button onClick={() => router.push('/subcategories')}>
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
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
                Manage Subcategories
              </Button>
            </CanAccess>
          </div>

          {category.subcategories && category.subcategories.length > 0 ? (
            <div className="divide-y divide-gray-200">
              {category.subcategories.map((subcategory, index) => (
                <div
                  key={`${subcategory.title}-${index}`}
                  className="py-4 flex items-center gap-3 hover:bg-gray-50 px-4 -mx-4 rounded transition-colors"
                >
                  <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                    <svg
                      className="w-4 h-4 text-blue-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                      />
                    </svg>
                  </div>
                  <h3 className="font-medium text-gray-900">{subcategory.title}</h3>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Subcategories</h3>
              <p className="text-gray-500 mb-4">
                This category doesn't have any subcategories yet.
              </p>
              <CanAccess permission="subcategories.list">
                <Button onClick={() => router.push('/subcategories')}>
                  Manage Subcategories
                </Button>
              </CanAccess>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}