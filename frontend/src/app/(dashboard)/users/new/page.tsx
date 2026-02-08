'use client';

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { UserForm } from '@/components/users';
import { LoadingOverlay } from '@/components/ui';
import { usePermissions } from '@/hooks/usePermissions';
import { api } from '@/lib/api';
import { User, RoleWithPermissions, ApiError } from '@/types';

export default function NewUserPage() {
  const searchParams = useSearchParams();
  const editId = searchParams.get('edit');
  const { hasAnyPermission } = usePermissions();

  const [user, setUser] = useState<User | null>(null);
  const [roles, setRoles] = useState<RoleWithPermissions[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        // Only fetch roles if user has permission to view them
        if (hasAnyPermission(['roles.list', 'roles.view'])) {
          const rolesData = await api.getRoles();
          // Handle both array and paginated response
          setRoles(Array.isArray(rolesData) ? rolesData : (rolesData as any).data || []);
        }

        if (editId) {
          const userData = await api.getUser(editId);
          setUser(userData);
        }
      } catch (error) {
        const apiError = error as ApiError;
        // Silently handle 403 errors (user lacks permission)
        if (apiError.status !== 403) {
          console.error('Failed to fetch data:', error);
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editId]);

  if (isLoading) {
    return <LoadingOverlay message="Loading..." />;
  }

  return (
    <div className="max-w-3xl mx-auto">
      <UserForm user={user || undefined} roles={roles} />
    </div>
  );
}
