'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Button, Card, LoadingOverlay, Modal } from '@/components/ui';
import { RoleTable } from '@/components/roles';
import { CanAccess } from '@/components/auth/CanAccess';
import { AccessDenied } from '@/components/auth/AccessDenied';
import { usePermissions } from '@/hooks/usePermissions';
import { api } from '@/lib/api';
import { Role, ApiError } from '@/types';

export default function RolesPage() {
  const { hasAnyPermission } = usePermissions();
  const [roles, setRoles] = useState<Role[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deleteRole, setDeleteRole] = useState<Role | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accessDenied, setAccessDenied] = useState(false);

  // Check if user has permission to view roles
  const canViewRoles = hasAnyPermission(['roles.list', 'roles.view']);

  const fetchRoles = async () => {
    // Check permission before fetching
    if (!canViewRoles) {
      setAccessDenied(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const data = await api.getRoles();
      console.log('Roles API response:', data);
      setRoles(data);
    } catch (err) {
      const apiError = err as ApiError;
      // Handle 403 errors gracefully
      if (apiError.status === 403) {
        setAccessDenied(true);
      } else {
        console.error('Failed to fetch roles:', err);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRoles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDelete = async () => {
    if (!deleteRole) return;

    setIsDeleting(true);
    setError(null);

    try {
      await api.deleteRole(deleteRole.id);
      setRoles((prev) => prev.filter((r) => r.id !== deleteRole.id));
      setDeleteRole(null);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || 'Failed to delete role');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleStatusToggle = async (role: Role, isActive: boolean) => {
    setIsUpdatingStatus(true);
    try {
      const updatedRole = await api.updateRoleStatus(role.id, isActive);
      setRoles((prev) =>
        prev.map((r) => (r.id === role.id ? { ...r, is_active: updatedRole.is_active } : r))
      );
    } catch (err) {
      const apiError = err as ApiError;
      console.error('Failed to update role status:', apiError);
      // Optionally show an error message to the user
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Roles</h1>
          <p className="text-gray-500">Manage roles and their permissions</p>
        </div>
        <CanAccess permission="roles.create">
          <Link href="/roles/new">
            <Button>
              <svg
                className="w-4 h-4 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
              Add Role
            </Button>
          </Link>
        </CanAccess>
      </div>

      <Card padding="none">
        {accessDenied ? (
          <AccessDenied resource="roles" />
        ) : isLoading || isUpdatingStatus ? (
          <LoadingOverlay message={isUpdatingStatus ? "Updating role status..." : "Loading roles..."} />
        ) : (
          <RoleTable
            roles={roles}
            onDelete={setDeleteRole}
            onStatusToggle={handleStatusToggle}
          />
        )}
      </Card>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deleteRole}
        onClose={() => setDeleteRole(null)}
        title="Delete Role"
      >
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm mb-4">
            {error}
          </div>
        )}
        <p className="text-gray-600">
          Are you sure you want to delete the role <strong>{deleteRole?.name}</strong>?
          {deleteRole?.user_count && deleteRole.user_count > 0 && (
            <span className="text-red-600 block mt-2">
              Warning: {deleteRole.user_count} user(s) currently have this role.
            </span>
          )}
        </p>
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={() => setDeleteRole(null)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDelete} isLoading={isDeleting}>
            Delete Role
          </Button>
        </div>
      </Modal>
    </div>
  );
}
