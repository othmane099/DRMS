'use client';

import React, { useState } from 'react';
import { Modal, Button, Select } from '@/components/ui';
import { api } from '@/lib/api';
import { User, RoleWithPermissions, ApiError } from '@/types';

interface RoleAssignModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: User;
  roles: RoleWithPermissions[];
  onRoleAssigned: (user: User) => void;
}

export function RoleAssignModal({
  isOpen,
  onClose,
  user,
  roles,
  onRoleAssigned,
}: RoleAssignModalProps) {
  // Get current role ID from either role_id field or role object
  const getCurrentRoleId = () => {
    return user.role?.id?.toString() || '';
  };

  const [selectedRoleId, setSelectedRoleId] = useState<string>(getCurrentRoleId());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset selectedRoleId whenever user or role changes
  React.useEffect(() => {
    const currentRoleId = getCurrentRoleId();
    setSelectedRoleId(currentRoleId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user.role?.id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const roleId = selectedRoleId || null;
      const updatedUser = await api.assignUserRole(user.id, roleId);
      onRoleAssigned(updatedUser);
    } catch (err) {
      const apiError = err as ApiError;
      console.error('Error assigning role:', apiError);
      setError(apiError.detail || 'Failed to assign role');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Assign Role">
      <form onSubmit={handleSubmit}>
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm mb-4">
            {error}
          </div>
        )}

        <p className="text-sm text-gray-600 mb-4">
          Assign a role to <strong>{user.first_name} {user.last_name}</strong>
        </p>

        <Select
          label="Role"
          value={selectedRoleId}
          onChange={(e) => setSelectedRoleId(e.target.value)}
          options={[
            { value: '', label: 'No Role' },
            ...roles.map((role) => ({ value: role.id, label: role.name })),
          ]}
        />

        <div className="flex justify-end gap-3 mt-6">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            Assign Role
          </Button>
        </div>
      </form>
    </Modal>
  );
}
