'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Input, Card, CardHeader } from '@/components/ui';
import { api } from '@/lib/api';
import { Category, CategoryCreateInput, CategoryUpdateInput, ApiError } from '@/types';

interface CategoryFormProps {
  category?: Category;
}

export function CategoryForm({ category }: CategoryFormProps) {
  const router = useRouter();
  const isEditing = !!category;

  const [formData, setFormData] = useState({
    title: category?.title || '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const validate = () => {
    const newErrors: Record<string, string> = {};

    // Validate title
    const trimmedTitle = formData.title.trim();
    if (!trimmedTitle) {
      newErrors.title = 'Category name is required';
    } else if (trimmedTitle.length > 255) {
      newErrors.title = 'Category name must not exceed 255 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsLoading(true);
    setApiError(null);

    try {
      const trimmedTitle = formData.title.trim();

      if (isEditing) {
        const updateData: CategoryUpdateInput = {
          title: trimmedTitle,
        };
        await api.updateCategory(category.id, updateData);
      } else {
        const createData: CategoryCreateInput = {
          title: trimmedTitle,
        };
        await api.createCategory(createData);
      }
      router.push('/categories');
    } catch (err) {
      const error = err as ApiError;
      setApiError(error.detail || 'Failed to save category');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: '' }));
    }
  };

  return (
    <Card>
      <CardHeader
        title={isEditing ? 'Edit Category' : 'Create Category'}
        description={isEditing ? 'Update category information' : 'Add a new category'}
      />

      <form onSubmit={handleSubmit} className="space-y-6">
        {apiError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
            {apiError}
          </div>
        )}

        <div className="space-y-6">
          <Input
            label="Category Name"
            value={formData.title}
            onChange={(e) => handleChange('title', e.target.value)}
            error={errors.title}
            placeholder="e.g., Electronics, Clothing, Furniture"
            required
            maxLength={255}
          />
        </div>

        <div className="flex justify-end gap-3 pt-6 border-t">
          <Button
            type="button"
            variant="secondary"
            onClick={() => router.push('/categories')}
          >
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {isEditing ? 'Update Category' : 'Create Category'}
          </Button>
        </div>
      </form>
    </Card>
  );
}