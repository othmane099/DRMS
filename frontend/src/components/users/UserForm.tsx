'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Input, Select, Card, CardHeader, Switch } from '@/components/ui';
import { api } from '@/lib/api';
import { User, UserCreateInput, UserUpdateInput, RoleWithPermissions, ApiError } from '@/types';

interface UserFormProps {
  user?: User;
  roles: RoleWithPermissions[];
}

export function UserForm({ user, roles }: UserFormProps) {
  const router = useRouter();
  const isEditing = !!user;

  const [formData, setFormData] = useState({
    username: user?.username || '',
    email: user?.email || '',
    phone: user?.phone || '',
    password: '',
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    is_active: user?.is_active ?? true,
    role_id: user?.role_id?.toString() || '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const validate = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.username.trim()) {
      newErrors.username = 'Username is required';
    }
    if (formData.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Invalid email format';
    }
    if (!isEditing && !formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password && formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }
    if (!formData.first_name.trim()) {
      newErrors.first_name = 'First name is required';
    }
    if (!formData.last_name.trim()) {
      newErrors.last_name = 'Last name is required';
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
        const updateData: UserUpdateInput = {
          username: formData.username,
          email: formData.email.trim() || undefined,
          phone: formData.phone.trim() || undefined,
          first_name: formData.first_name,
          last_name: formData.last_name,
          is_active: formData.is_active,
          role_id: formData.role_id || undefined,
        };
        if (formData.password) {
          updateData.password = formData.password;
        }
        await api.updateUser(user.id, updateData);
      } else {
        const createData: UserCreateInput = {
          username: formData.username,
          email: formData.email.trim() || undefined,
          phone: formData.phone.trim() || undefined,
          password: formData.password,
          first_name: formData.first_name,
          last_name: formData.last_name,
          is_active: formData.is_active,
          role_id: formData.role_id || undefined,
        };
        await api.createUser(createData);
      }
      router.push('/users');
    } catch (err) {
      const error = err as ApiError;
      setApiError(error.detail || 'Failed to save user');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (field: string, value: string | boolean) => {
    setFormData((prev) => ({
      ...prev,
      [field]: field === 'is_active' ? value === 'true' || value === true : value
    }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: '' }));
    }
  };

  return (
    <Card>
      <CardHeader
        title={isEditing ? 'Edit User' : 'Create User'}
        description={isEditing ? 'Update user information' : 'Add a new user to the system'}
      />

      <form onSubmit={handleSubmit} className="space-y-6">
        {apiError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
            {apiError}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Input
            label="First Name"
            value={formData.first_name}
            onChange={(e) => handleChange('first_name', e.target.value)}
            error={errors.first_name}
            required
          />

          <Input
            label="Last Name"
            value={formData.last_name}
            onChange={(e) => handleChange('last_name', e.target.value)}
            error={errors.last_name}
            required
          />

          <Input
            label="Username"
            value={formData.username}
            onChange={(e) => handleChange('username', e.target.value)}
            error={errors.username}
            required
          />

          <Input
            label="Email"
            type="email"
            value={formData.email}
            onChange={(e) => handleChange('email', e.target.value)}
            error={errors.email}
          />

          <Input
            label="Phone"
            type="tel"
            value={formData.phone}
            onChange={(e) => handleChange('phone', e.target.value)}
            placeholder="+1234567890"
          />

          <Input
            label={isEditing ? 'Password (leave blank to keep current)' : 'Password'}
            type="password"
            value={formData.password}
            onChange={(e) => handleChange('password', e.target.value)}
            error={errors.password}
            required={!isEditing}
          />

          <Select
            label="Role"
            value={formData.role_id}
            onChange={(e) => handleChange('role_id', e.target.value)}
            options={[
              { value: '', label: 'No Role' },
              ...roles.map((role) => ({ value: role.id, label: role.name })),
            ]}
          />
        </div>

        <div className="border-t pt-6">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">Account Status</label>
              <p className="text-sm text-gray-500">
                {formData.is_active ? 'Account is active and can access the system' : 'Account is inactive and cannot log in'}
              </p>
            </div>
            <Switch
              checked={formData.is_active}
              onChange={(checked) => handleChange('is_active', String(checked))}
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-6 border-t">
          <Button
            type="button"
            variant="secondary"
            onClick={() => router.push('/users')}
          >
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {isEditing ? 'Update User' : 'Create User'}
          </Button>
        </div>
      </form>
    </Card>
  );
}
