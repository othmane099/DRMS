'use client';

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { RoleForm } from '@/components/roles';
import { LoadingOverlay } from '@/components/ui';
import { usePermissions } from '@/hooks/usePermissions';
import { api } from '@/lib/api';
import { RoleWithPermissions, Permission, ApiError } from '@/types';

export default function NewRolePage() {
  const searchParams = useSearchParams();
  const editId = searchParams.get('edit');
  const { hasAnyPermission } = usePermissions();

  const [role, setRole] = useState<RoleWithPermissions | null>(null);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        // Only fetch permissions if user has permission to view them
        if (hasAnyPermission(['permissions.list'])) {
          const permissionsData = await api.getPermissions();
          console.log('Permissions API response:', permissionsData);
          // Handle both array and paginated response
          setPermissions(Array.isArray(permissionsData) ? permissionsData : (permissionsData as any).data || []);
        }

        if (editId) {
          const roleData = await api.getRole(editId);
          setRole(roleData);
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
    <div className="max-w-4xl mx-auto">
      <RoleForm role={role || undefined} permissions={permissions} />
    </div>
  );
}
