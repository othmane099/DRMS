'use client';

import React, { useState } from 'react';
import { Modal, Button, Input, Select } from '@/components/ui';
import { api } from '@/lib/api';
import { Subcategory, SubcategoryCreateInput, SubcategoryUpdateInput, Category, ApiError } from '@/types';

interface SubcategoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  subcategory?: Subcategory;
  categories: Category[];
  onSuccess: () => void;
}

export function SubcategoryModal({ isOpen, onClose, subcategory, categories, onSuccess }: SubcategoryModalProps) {
  const isEditing = !!subcategory;

  const [formData, setFormData] = useState({
    title: subcategory?.title || '',
    category_id: subcategory?.category_id || '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Reset form when modal opens/closes or subcategory changes
  React.useEffect(() => {
    if (isOpen) {
      setFormData({
        title: subcategory?.title || '',
        category_id: subcategory?.category_id || '',
      });
      setErrors({});
      setApiError(null);
    }
  }, [isOpen, subcategory]);

  const validate = () => {
    const newErrors: Record<string, string> = {};

    // Validate title
    const trimmedTitle = formData.title.trim();
    if (!trimmedTitle) {
      newErrors.title = 'Subcategory name is required';
    } else if (trimmedTitle.length > 255) {
      newErrors.title = 'Subcategory name must not exceed 255 characters';
    }

    // Validate category
    if (!formData.category_id) {
      newErrors.category_id = 'Category is required';
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

      if (isEditing && subcategory) {
        const updateData: SubcategoryUpdateInput = {
          title: trimmedTitle,
          category_id: formData.category_id,
        };
        await api.updateSubcategory(subcategory.id, updateData);
      } else {
        const createData: SubcategoryCreateInput = {
          title: trimmedTitle,
          category_id: formData.category_id,
        };
        await api.createSubcategory(createData);
      }
      onSuccess();
      onClose();
    } catch (err) {
      const error = err as ApiError;
      setApiError(error.detail || 'Failed to save subcategory');
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
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Edit Subcategory' : 'Create Subcategory'}
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {apiError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
            {apiError}
          </div>
        )}

        <div className="space-y-6">
          <Input
            label="Subcategory Name"
            value={formData.title}
            onChange={(e) => handleChange('title', e.target.value)}
            error={errors.title}
            placeholder="e.g., Annual Reports, Invoices, Contracts"
            required
            maxLength={255}
          />

          <Select
            label="Category"
            value={formData.category_id}
            onChange={(e) => handleChange('category_id', e.target.value)}
            options={[
              { value: '', label: 'Select a category' },
              ...categories.map((category) => ({
                value: category.id,
                label: category.title,
              })),
            ]}
            error={errors.category_id}
            className="w-full"
          />
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {isEditing ? 'Update Subcategory' : 'Create Subcategory'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}