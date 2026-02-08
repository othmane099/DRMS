'use client';

import React, { useState } from 'react';
import { Modal, Button, Input } from '@/components/ui';
import { api } from '@/lib/api';
import { Tag, TagCreateInput, TagUpdateInput, ApiError } from '@/types';

interface TagModalProps {
  isOpen: boolean;
  onClose: () => void;
  tag?: Tag;
  onSuccess: () => void;
}

export function TagModal({ isOpen, onClose, tag, onSuccess }: TagModalProps) {
  const isEditing = !!tag;

  const [formData, setFormData] = useState({
    title: tag?.title || '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Reset form when modal opens/closes or tag changes
  React.useEffect(() => {
    if (isOpen) {
      setFormData({
        title: tag?.title || '',
      });
      setErrors({});
      setApiError(null);
    }
  }, [isOpen, tag]);

  const validate = () => {
    const newErrors: Record<string, string> = {};

    // Validate title
    const trimmedTitle = formData.title.trim();
    if (!trimmedTitle) {
      newErrors.title = 'Tag name is required';
    } else if (trimmedTitle.length > 255) {
      newErrors.title = 'Tag name must not exceed 255 characters';
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

      if (isEditing && tag) {
        const updateData: TagUpdateInput = {
          title: trimmedTitle,
        };
        await api.updateTag(tag.id, updateData);
      } else {
        const createData: TagCreateInput = {
          title: trimmedTitle,
        };
        await api.createTag(createData);
      }
      onSuccess();
      onClose();
    } catch (err) {
      const error = err as ApiError;
      setApiError(error.detail || 'Failed to save tag');
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
      title={isEditing ? 'Edit Tag' : 'Create Tag'}
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {apiError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
            {apiError}
          </div>
        )}

        <div className="space-y-6">
          <Input
            label="Tag Name"
            value={formData.title}
            onChange={(e) => handleChange('title', e.target.value)}
            error={errors.title}
            placeholder="e.g., High Priority, Urgent, Draft"
            required
            maxLength={255}
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
            {isEditing ? 'Update Tag' : 'Create Tag'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
