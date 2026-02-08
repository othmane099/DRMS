import { useAuth } from './useAuth';

/**
 * Hook to check if the current user has specific permissions
 *
 * @example
 * const { hasPermission, hasAnyPermission, hasAllPermissions } = usePermissions();
 *
 * if (hasPermission('users.create')) {
 *   // Show "Add User" button
 * }
 */
export function usePermissions() {
  const { user } = useAuth();

  /**
   * Get all permissions for the current user (from role and custom permissions)
   */
  const getUserPermissions = (): string[] => {
    if (!user) return [];

    // Superusers bypass all permission checks
    if (user.is_superuser) {
      return ['*']; // Special wildcard indicating all permissions
    }

    // If user is inactive, they have NO permissions
    if (user.is_active === false) {
      return [];
    }

    // If user has a role and that role is inactive, they have NO permissions
    // This overrides even custom permissions - inactive role means no access
    if (user.role && user.role.is_active === false) {
      return [];
    }

    const permissions: string[] = [];

    // Add permissions from role (only if role is active or is_active is undefined/null)
    if (user.role?.permissions) {
      user.role.permissions.forEach((perm) => {
        if (typeof perm === 'string') {
          permissions.push(perm);
        } else if (perm.code) {
          permissions.push(perm.code);
        }
      });
    }

    // Add custom permissions
    if (user.custom_permissions) {
      user.custom_permissions.forEach((perm) => {
        if (typeof perm === 'string') {
          permissions.push(perm);
        } else if (perm.code) {
          permissions.push(perm.code);
        }
      });
    }

    // Remove duplicates
    return [...new Set(permissions)];
  };

  /**
   * Check if user has a specific permission
   *
   * @param permissionCode - The permission code to check (e.g., "users.create")
   * @returns true if user has the permission or is a superuser
   */
  const hasPermission = (permissionCode: string): boolean => {
    if (!user) return false;

    // Superusers have all permissions
    if (user.is_superuser) return true;

    const userPermissions = getUserPermissions();
    return userPermissions.includes(permissionCode);
  };

  /**
   * Check if user has ANY of the specified permissions
   *
   * @param permissionCodes - Array of permission codes
   * @returns true if user has at least one of the permissions
   */
  const hasAnyPermission = (permissionCodes: string[]): boolean => {
    if (!user) return false;
    if (user.is_superuser) return true;

    return permissionCodes.some(code => hasPermission(code));
  };

  /**
   * Check if user has ALL of the specified permissions
   *
   * @param permissionCodes - Array of permission codes
   * @returns true if user has all of the permissions
   */
  const hasAllPermissions = (permissionCodes: string[]): boolean => {
    if (!user) return false;
    if (user.is_superuser) return true;

    return permissionCodes.every(code => hasPermission(code));
  };

  /**
   * Check if user is a superuser
   */
  const isSuperuser = (): boolean => {
    return user?.is_superuser === true;
  };

  return {
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    isSuperuser,
    permissions: getUserPermissions(),
  };
}