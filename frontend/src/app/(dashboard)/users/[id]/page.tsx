'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Button,
  Card,
  CardHeader,
  Badge,
  LoadingOverlay,
  Modal,
} from '@/components/ui';
import {
  UserStatusToggle,
  RoleAssignModal,
  PermissionModal,
} from '@/components/users';
import { CanAccess } from '@/components/auth/CanAccess';
import { usePermissions } from '@/hooks/usePermissions';
import { api } from '@/lib/api';
import { User, RoleWithPermissions, Permission, ApiError } from '@/types';
import { formatDateTime, getInitials } from '@/lib/utils';

type Tab = 'profile' | 'permissions';

export default function UserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const userId = params.id as string;
  const { hasAnyPermission } = usePermissions();

  const [user, setUser] = useState<User | null>(null);
  const [roles, setRoles] = useState<RoleWithPermissions[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>('profile');
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [showPermissionModal, setShowPermissionModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        // Fetch user data
        const userData = await api.getUser(userId);
        setUser(userData);

        // Conditionally fetch roles and permissions based on user's permissions
        const fetchPromises: Promise<any>[] = [];

        if (hasAnyPermission(['roles.list', 'roles.view'])) {
          fetchPromises.push(
            api.getRoles().catch((err) => {
              const apiError = err as ApiError;
              if (apiError.status !== 403) {
                console.error('Failed to fetch roles:', err);
              }
              return [];
            })
          );
        } else {
          fetchPromises.push(Promise.resolve([]));
        }

        if (hasAnyPermission(['permissions.list'])) {
          fetchPromises.push(
            api.getPermissions().catch((err) => {
              const apiError = err as ApiError;
              if (apiError.status !== 403) {
                console.error('Failed to fetch permissions:', err);
              }
              return [];
            })
          );
        } else {
          fetchPromises.push(Promise.resolve([]));
        }

        const [rolesData, permissionsData] = await Promise.all(fetchPromises);

        // Handle both array and paginated response for roles and permissions
        const processedRoles = Array.isArray(rolesData) ? rolesData : (rolesData as any).data || [];
        const processedPermissions = Array.isArray(permissionsData) ? permissionsData : (permissionsData as any).data || [];

        setRoles(processedRoles);
        setPermissions(processedPermissions);
      } catch (err) {
        const apiError = err as ApiError;
        console.error('Error fetching data:', apiError);
        setError(apiError.detail || 'Failed to load user');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.deleteUser(userId);
      router.push('/users');
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || 'Failed to delete user');
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  if (isLoading) {
    return <LoadingOverlay message="Loading user..." />;
  }

  if (error || !user) {
    return (
      <Card>
        <div className="text-center py-12">
          <p className="text-red-600 mb-4">{error || 'User not found'}</p>
          <Button variant="secondary" onClick={() => router.push('/users')}>
            Back to Users
          </Button>
        </div>
      </Card>
    );
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'profile', label: 'Profile' },
    { id: 'permissions', label: 'Permissions' },
  ];

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/users')}
            className="p-2 hover:bg-gray-100 rounded-md"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
          <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center text-xl font-medium">
            {getInitials(user.first_name, user.last_name)}
          </div>
          <div>
            <h1 className="text-2xl font-bold">
              {user.first_name} {user.last_name}
            </h1>
            <p className="text-gray-500">@{user.username}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <CanAccess permission="users.update">
            <Button variant="secondary" onClick={() => router.push(`/users/new?edit=${userId}`)}>
              Edit
            </Button>
          </CanAccess>
          <CanAccess permission="users.delete">
            <Button variant="danger" onClick={() => setShowDeleteModal(true)}>
              Delete
            </Button>
          </CanAccess>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-3 border-b-2 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'border-black text-black'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'profile' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader title="User Information" />
            <dl className="space-y-4">
              <div>
                <dt className="text-sm text-gray-500">Email</dt>
                <dd className="mt-1">{user.email || 'Not provided'}</dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">Status</dt>
                <dd className="mt-1 flex items-center gap-3">
                  <Badge variant={user.is_active ? 'success' : 'danger'}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                  <CanAccess permission="users.update">
                    <UserStatusToggle
                      user={user}
                      onStatusChange={(updatedUser) => setUser(updatedUser)}
                    />
                  </CanAccess>
                </dd>
              </div>
              {user.created_at && (
                <div>
                  <dt className="text-sm text-gray-500">Created</dt>
                  <dd className="mt-1">{formatDateTime(user.created_at)}</dd>
                </div>
              )}
              {user.updated_at && (
                <div>
                  <dt className="text-sm text-gray-500">Last Updated</dt>
                  <dd className="mt-1">{formatDateTime(user.updated_at)}</dd>
                </div>
              )}
              {user.last_login && (
                <div>
                  <dt className="text-sm text-gray-500">Last Login</dt>
                  <dd className="mt-1">{formatDateTime(user.last_login)}</dd>
                </div>
              )}
            </dl>
          </Card>

          <Card key={`role-card-${user.role?.id || 'no-role'}`}>
            <CardHeader
              title="Role"
              action={
                <CanAccess permission="users.update">
                  <Button variant="ghost" size="sm" onClick={() => setShowRoleModal(true)}>
                    Change Role
                  </Button>
                </CanAccess>
              }
            />
            {user.role ? (
              <div key={`role-content-${user.role.id}`}>
                <div className="flex items-center gap-2 mb-2">
                  <Badge>{user.role.name}</Badge>
                </div>
                <p className="text-sm text-gray-500 mb-3">{user.role.description}</p>
                {user.role.permissions && Array.isArray(user.role.permissions) && user.role.permissions.length > 0 ? (
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-2">
                      Inherited Permissions ({user.role.permissions.length})
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {user.role.permissions.map((permission, index) => (
                        <Badge key={typeof permission === 'string' ? permission : permission.id || index}>
                          {typeof permission === 'string' ? permission : permission.name}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-400">No permissions inherited from role</p>
                )}
              </div>
            ) : (
              <p className="text-gray-500">No role assigned</p>
            )}
          </Card>
        </div>
      )}

      {activeTab === 'permissions' && (
        <Card>
          <CardHeader
            title="User Permissions"
            description="Permissions directly assigned to this user (in addition to role permissions)"
            action={
              <CanAccess permission="users.update">
                <Button variant="ghost" size="sm" onClick={() => setShowPermissionModal(true)}>
                  Manage Permissions
                </Button>
              </CanAccess>
            }
          />
          {user.custom_permissions && user.custom_permissions.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {user.custom_permissions.map((permission, index) => (
                <Badge key={typeof permission === 'string' ? permission : permission.id || index}>
                  {typeof permission === 'string' ? permission : permission.name}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No direct permissions assigned</p>
          )}
        </Card>
      )}

      {/* Modals */}
      {showRoleModal && (
        <RoleAssignModal
          isOpen={showRoleModal}
          onClose={() => setShowRoleModal(false)}
          user={user}
          roles={roles}
          onRoleAssigned={async (updatedUser) => {
            // Refetch the user to get the complete data
            try {
              const freshUser = await api.getUser(userId);
              setUser(freshUser);
            } catch (err) {
              console.error('Error refreshing user:', err);
              // Fallback to the API response
              setUser({ ...updatedUser });
            }
            setShowRoleModal(false);
          }}
        />
      )}

      {showPermissionModal && (
        <PermissionModal
          isOpen={showPermissionModal}
          onClose={() => setShowPermissionModal(false)}
          user={user}
          allPermissions={permissions}
          onPermissionsUpdated={(updatedUser) => {
            setUser(updatedUser);
          }}
        />
      )}

      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete User"
      >
        <p className="text-gray-600">
          Are you sure you want to delete <strong>{user.first_name} {user.last_name}</strong>?
          This action cannot be undone.
        </p>
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={() => setShowDeleteModal(false)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDelete} isLoading={isDeleting}>
            Delete User
          </Button>
        </div>
      </Modal>
    </div>
  );
}
