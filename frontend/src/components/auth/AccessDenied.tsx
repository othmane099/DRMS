'use client';

interface AccessDeniedProps {
  /**
   * The resource that the user is trying to access
   * e.g., "users", "roles", "logged history"
   */
  resource: string;

  /**
   * Optional custom message
   */
  message?: string;
}

/**
 * Component to display when user doesn't have permission to access a page or resource
 *
 * @example
 * <AccessDenied resource="users" />
 */
export function AccessDenied({ resource, message }: AccessDeniedProps) {
  return (
    <div className="py-12 text-center">
      <svg
        className="mx-auto h-12 w-12 text-gray-400 mb-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
        />
      </svg>
      <h3 className="text-lg font-medium text-gray-900 mb-2">Access Denied</h3>
      <p className="text-gray-500">
        {message || `You don't have permission to view ${resource}.`}
      </p>
      <p className="text-sm text-gray-400 mt-2">
        Contact your administrator to request access.
      </p>
    </div>
  );
}