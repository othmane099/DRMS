'use client';

import React, { useState } from 'react';
import { Switch } from '@/components/ui';
import { api } from '@/lib/api';
import { User, ApiError } from '@/types';

interface UserStatusToggleProps {
  user: User;
  onStatusChange?: (user: User) => void;
}

export function UserStatusToggle({ user, onStatusChange }: UserStatusToggleProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleToggle = async (checked: boolean) => {
    setIsLoading(true);
    setError(null);

    try {
      const updatedUser = await api.updateUserStatus(user.id, checked);
      onStatusChange?.(updatedUser);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || 'Failed to update status');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <Switch
        checked={user.is_active}
        onChange={handleToggle}
        disabled={isLoading}
      />
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  );
}
