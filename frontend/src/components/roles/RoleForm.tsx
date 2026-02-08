'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Input, Card, CardHeader } from '@/components/ui';
import { PermissionChecklist } from './PermissionChecklist';
import { api } from '@/lib/api';
import { RoleWithPermissions, Permission, RoleCreateInput, RoleUpdateInput, ApiError } from '@/types';

interface RoleFormProps {
  role?: RoleWithPermissions;
  permissions: Permission[];
}

export function RoleForm({ role, permissions }: RoleFormProps) {
  const router = useRouter();
  const isEditing = !!role;

  const [formData, setFormData] = useState({
    name: role?.name || '',
    description: role?.description || '',
  });
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>(() => {
    if (!role?.permissions) return [];
    return (role.permissions as (Permission | string)[]).map(p => {
      if (typeof p === 'string') return p;
      return p.code;
    });
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const validate = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Role name is required';
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
      if (isEditing) {
        const updateData: RoleUpdateInput = {
          name: formData.name,
          description: formData.description,
          permissions: selectedPermissions,
        };
        await api.updateRole(role.id, updateData);
      } else {
        const createData: RoleCreateInput = {
          name: formData.name,
          description: formData.description,
          permissions: selectedPermissions,
        };
        await api.createRole(createData);
      }
      router.push('/roles');
    } catch (err) {
      const error = err as ApiError;
      setApiError(error.detail || 'Failed to save role');
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
    <form onSubmit={handleSubmit} className="space-y-6">
      <Card>
        <CardHeader
          title={isEditing ? 'Edit Role' : 'Create Role'}
          description={isEditing ? 'Update role information' : 'Create a new role with permissions'}
        />

        {apiError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm mb-6">
            {apiError}
          </div>
        )}

        <div className="space-y-4">
          <Input
            label="Role Name"
            value={formData.name}
            onChange={(e) => handleChange('name', e.target.value)}
            error={errors.name}
            placeholder="e.g., Manager, Editor, Viewer"
            required
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              placeholder="Describe the purpose of this role..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
            />
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Permissions"
          description="Select the permissions for this role"
        />
        <PermissionChecklist
          permissions={permissions}
          selectedPermissions={selectedPermissions}
          onSelectionChange={setSelectedPermissions}
        />
      </Card>

      <div className="flex justify-end gap-3">
        <Button
          type="button"
          variant="secondary"
          onClick={() => router.push('/roles')}
        >
          Cancel
        </Button>
        <Button type="submit" isLoading={isLoading}>
          {isEditing ? 'Update Role' : 'Create Role'}
        </Button>
      </div>
    </form>
  );
}
