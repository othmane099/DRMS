'use client';

import React, { useState } from 'react';
import { Modal, Button, Input } from '@/components/ui';
import { api } from '@/lib/api';
import { ApiError } from '@/types';

interface ChangePasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function ChangePasswordModal({ isOpen, onClose, onSuccess }: ChangePasswordModalProps) {
  const [formData, setFormData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  React.useEffect(() => {
    if (isOpen) {
      setFormData({ currentPassword: '', newPassword: '', confirmPassword: '' });
      setErrors({});
      setApiError(null);
    }
  }, [isOpen]);

  const validate = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.currentPassword) {
      newErrors.currentPassword = 'Current password is required';
    }

    if (!formData.newPassword) {
      newErrors.newPassword = 'New password is required';
    } else if (formData.newPassword.length < 6) {
      newErrors.newPassword = 'Password should have at least 6 characters';
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your new password';
    } else if (formData.newPassword !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
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
      await api.updatePassword({
        current_password: formData.currentPassword,
        new_password: formData.newPassword,
      });
      onClose();
      onSuccess?.();
    } catch (err) {
      const error = err as ApiError;
      setApiError(error.detail || 'Failed to update password.');
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
    <Modal isOpen={isOpen} onClose={onClose} title="Change Password" size="sm">
      <form onSubmit={handleSubmit} className="space-y-6">
        {apiError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
            {apiError}
          </div>
        )}
        <div className="space-y-6">
          <Input
            label="Current Password"
            type="password"
            value={formData.currentPassword}
            onChange={(e) => handleChange('currentPassword', e.target.value)}
            error={errors.currentPassword}
            required
          />
          <Input
            label="New Password"
            type="password"
            value={formData.newPassword}
            onChange={(e) => handleChange('newPassword', e.target.value)}
            error={errors.newPassword}
            required
          />
          <Input
            label="Confirm New Password"
            type="password"
            value={formData.confirmPassword}
            onChange={(e) => handleChange('confirmPassword', e.target.value)}
            error={errors.confirmPassword}
            required
          />
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            Update Password
          </Button>
        </div>
      </form>
    </Modal>
  );
}