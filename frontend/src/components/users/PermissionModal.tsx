'use client';

import React, { useState, useMemo } from 'react';
import { Modal, Button, Checkbox } from '@/components/ui';
import { api } from '@/lib/api';
import { User, Permission, ApiError } from '@/types';

interface PermissionModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: User;
  allPermissions: Permission[];
  onPermissionsUpdated: (user: User) => void;
}

export function PermissionModal({
  isOpen,
  onClose,
  user,
  allPermissions,
  onPermissionsUpdated,
}: PermissionModalProps) {
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>(
    user.custom_permissions?.map((p) => (typeof p === 'string' ? p : p.code)) || []
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Group permissions by module
  const permissionsByModule = useMemo(() => {
    return allPermissions.reduce((acc, permission) => {
      const module = permission.code.split('.')[0] || 'general';
      if (!acc[module]) {
        acc[module] = [];
      }
      acc[module].push(permission);
      return acc;
    }, {} as Record<string, Permission[]>);
  }, [allPermissions]);

  const handleToggle = (permissionCode: string) => {
    setSelectedPermissions((prev) =>
      prev.includes(permissionCode)
        ? prev.filter((code) => code !== permissionCode)
        : [...prev, permissionCode]
    );
  };

  const handleSelectAllModule = (module: string) => {
    const modulePermissionCodes = permissionsByModule[module].map((p) => p.code);
    const allSelected = modulePermissionCodes.every((code) => selectedPermissions.includes(code));

    if (allSelected) {
      setSelectedPermissions((prev) => prev.filter((code) => !modulePermissionCodes.includes(code)));
    } else {
      setSelectedPermissions((prev) => [...new Set([...prev, ...modulePermissionCodes])]);
    }
  };

  const handleSelectAll = () => {
    if (selectedPermissions.length === allPermissions.length) {
      setSelectedPermissions([]);
    } else {
      setSelectedPermissions(allPermissions.map((p) => p.code));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.updateUserPermissions(user.id, selectedPermissions);
      // Merge the response with the existing user data to preserve fields not in the response
      const updatedUser: User = {
        ...user,
        username: response.username,
        custom_permissions: response.custom_permissions,
        // Update role permissions if role exists
        role: user.role ? {
          ...user.role,
          permissions: response.role_permissions,
        } : user.role,
      };
      onPermissionsUpdated(updatedUser);
      onClose();
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || 'Failed to update permissions');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Manage Permissions" size="lg">
      <form onSubmit={handleSubmit}>
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm mb-4">
            {error}
          </div>
        )}

        <div className="flex justify-between items-center mb-4">
          <p className="text-sm text-gray-600">
            Managing permissions for <strong>{user.first_name} {user.last_name}</strong>
          </p>
          <Button type="button" variant="ghost" size="sm" onClick={handleSelectAll}>
            {selectedPermissions.length === allPermissions.length ? 'Deselect All' : 'Select All'}
          </Button>
        </div>

        <div className="max-h-96 overflow-y-auto space-y-6">
          {Object.entries(permissionsByModule).map(([module, permissions]) => {
            const modulePermissionCodes = permissions.map((p) => p.code);
            const allModuleSelected = modulePermissionCodes.every((code) =>
              selectedPermissions.includes(code)
            );

            return (
              <div key={module} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium text-sm uppercase text-gray-500">{module}</h4>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSelectAllModule(module)}
                  >
                    {allModuleSelected ? 'Deselect' : 'Select All'}
                  </Button>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {permissions.map((permission) => (
                    <Checkbox
                      key={permission.id}
                      label={permission.name}
                      checked={selectedPermissions.includes(permission.code)}
                      onChange={() => handleToggle(permission.code)}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            Save Permissions
          </Button>
        </div>
      </form>
    </Modal>
  );
}
