'use client';

import { ReactNode } from 'react';
import { usePermissions } from '@/hooks/usePermissions';

interface CanAccessProps {
  /**
   * Single permission code or array of permission codes
   * Format: "resource.action" (e.g., "users.create")
   */
  permission?: string | string[];

  /**
   * If true, user needs ALL permissions in the array
   * If false, user needs ANY permission in the array (default)
   */
  requireAll?: boolean;

  /**
   * Content to render if user has permission
   */
  children: ReactNode;

  /**
   * Optional fallback content to render if user lacks permission
   */
  fallback?: ReactNode;

  /**
   * If true, allow superusers to bypass permission check (default: true)
   */
  allowSuperuser?: boolean;
}

/**
 * Component to conditionally render children based on user permissions
 *
 * @example
 * // Single permission
 * <CanAccess permission="users.create">
 *   <button>Add User</button>
 * </CanAccess>
 *
 * @example
 * // Any of multiple permissions
 * <CanAccess permission={["users.view", "users.list"]}>
 *   <Link href="/users">Users</Link>
 * </CanAccess>
 *
 * @example
 * // All permissions required
 * <CanAccess permission={["users.view", "roles.view"]} requireAll>
 *   <ComplexComponent />
 * </CanAccess>
 *
 * @example
 * // With fallback
 * <CanAccess permission="users.delete" fallback={<span>Access Denied</span>}>
 *   <button>Delete User</button>
 * </CanAccess>
 */
export function CanAccess({
  permission,
  requireAll = false,
  children,
  fallback = null,
  allowSuperuser = true,
}: CanAccessProps) {
  const { hasPermission, hasAnyPermission, hasAllPermissions, isSuperuser } = usePermissions();

  // If no permission specified, render children (public content)
  if (!permission) {
    return <>{children}</>;
  }

  // Superusers bypass all checks
  if (allowSuperuser && isSuperuser()) {
    return <>{children}</>;
  }

  // Single permission check
  if (typeof permission === 'string') {
    return hasPermission(permission) ? <>{children}</> : <>{fallback}</>;
  }

  // Multiple permissions check
  const hasAccess = requireAll
    ? hasAllPermissions(permission)
    : hasAnyPermission(permission);

  return hasAccess ? <>{children}</> : <>{fallback}</>;
}