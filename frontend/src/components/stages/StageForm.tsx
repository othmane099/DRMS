'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Input, Card, CardHeader } from '@/components/ui';
import { api } from '@/lib/api';
import { Stage, StageCreateInput, StageUpdateInput, ApiError } from '@/types';

interface StageFormProps {
  stage?: Stage;
}

export function StageForm({ stage }: StageFormProps) {
  const router = useRouter();
  const isEditing = !!stage;

  const [formData, setFormData] = useState({
    title: stage?.title || '',
    color: stage?.color || '#3B82F6',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const validate = () => {
    const newErrors: Record<string, string> = {};

    // Validate title
    const trimmedTitle = formData.title.trim();
    if (!trimmedTitle) {
      newErrors.title = 'Stage name is required';
    } else if (trimmedTitle.length > 255) {
      newErrors.title = 'Stage name must not exceed 255 characters';
    }

    // Validate color - must be valid hex format
    const hexColorRegex = /^#[0-9A-Fa-f]{6}$/;
    if (!formData.color) {
      newErrors.color = 'Color is required';
    } else if (!hexColorRegex.test(formData.color)) {
      newErrors.color = 'Color must be in hex format (#RRGGBB)';
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
        const updateData: StageUpdateInput = {
          title: trimmedTitle,
          color: formData.color,
        };
        await api.updateStage(stage.id, updateData);
      } else {
        const createData: StageCreateInput = {
          title: trimmedTitle,
          color: formData.color,
        };
        await api.createStage(createData);
      }
      router.push('/stages');
    } catch (err) {
      const error = err as ApiError;
      setApiError(error.detail || 'Failed to save stage');
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
        title={isEditing ? 'Edit Stage' : 'Create Stage'}
        description={isEditing ? 'Update stage information' : 'Add a new workflow stage'}
      />

      <form onSubmit={handleSubmit} className="space-y-6">
        {apiError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
            {apiError}
          </div>
        )}

        <div className="space-y-6">
          <Input
            label="Stage Name"
            value={formData.title}
            onChange={(e) => handleChange('title', e.target.value)}
            error={errors.title}
            placeholder="e.g., Draft, Review, Approved"
            required
            maxLength={255}
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Color <span className="text-red-500">*</span>
            </label>
            <div className="flex items-center gap-4">
              <input
                type="color"
                value={formData.color}
                onChange={(e) => handleChange('color', e.target.value.toUpperCase())}
                className="h-12 w-24 rounded border border-gray-300 cursor-pointer"
              />
              <Input
                type="text"
                value={formData.color}
                onChange={(e) => handleChange('color', e.target.value.toUpperCase())}
                error={errors.color}
                placeholder="#3B82F6"
                className="flex-1 font-mono"
                maxLength={7}
              />
              <div
                className="w-12 h-12 rounded border border-gray-300"
                style={{ backgroundColor: formData.color }}
              />
            </div>
            {errors.color && (
              <p className="mt-1 text-sm text-red-600">{errors.color}</p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              Select a color or enter a hex code (e.g., #3B82F6)
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-6 border-t">
          <Button
            type="button"
            variant="secondary"
            onClick={() => router.push('/stages')}
          >
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {isEditing ? 'Update Stage' : 'Create Stage'}
          </Button>
        </div>
      </form>
    </Card>
  );
}