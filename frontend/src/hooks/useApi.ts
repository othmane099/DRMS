'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import {
  User,
  RoleWithPermissions,
  Permission,
  LoggedHistory,
  PaginatedResponse,
  UserFilters,
  ActivityFilters,
  ApiError, Role,
} from '@/types';

interface UseApiState<T> {
  data: T | null;
  isLoading: boolean;
  error: ApiError | null;
  refetch: () => Promise<void>;
}

// Generic hook for fetching data
function useApiQuery<T>(
  fetchFn: () => Promise<T>,
  dependencies: unknown[] = []
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await fetchFn();
      setData(result);
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setIsLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, isLoading, error, refetch: fetch };
}

// Users hooks
export function useUsers(filters?: UserFilters) {
  return useApiQuery<PaginatedResponse<User>>(
    () => api.getUsers(filters),
    [JSON.stringify(filters)]
  );
}

export function useUser(id: string) {
  return useApiQuery<User>(() => api.getUser(id), [id]);
}

// Roles hooks
export function useRoles() {
  return useApiQuery<Role[]>(() => api.getRoles(), []);
}

export function useRole(id: string) {
  return useApiQuery<RoleWithPermissions>(() => api.getRole(id), [id]);
}

// Permissions hook
export function usePermissions() {
  return useApiQuery<Permission[]>(() => api.getPermissions(), []);
}

// Activity logs hook
export function useActivityLogs(filters?: ActivityFilters) {
  return useApiQuery<PaginatedResponse<LoggedHistory>>(
    () => api.getActivityLogs(filters),
    [JSON.stringify(filters)]
  );
}

// Mutation hooks
interface UseMutationOptions<T, TData> {
  onSuccess?: (data: T) => void;
  onError?: (error: ApiError) => void;
}

interface UseMutationResult<T, TData> {
  mutate: (data: TData) => Promise<T | undefined>;
  isLoading: boolean;
  error: ApiError | null;
}

export function useMutation<T, TData = void>(
  mutationFn: (data: TData) => Promise<T>,
  options?: UseMutationOptions<T, TData>
): UseMutationResult<T, TData> {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const mutate = async (data: TData): Promise<T | undefined> => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await mutationFn(data);
      options?.onSuccess?.(result);
      return result;
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError);
      options?.onError?.(apiError);
      return undefined;
    } finally {
      setIsLoading(false);
    }
  };

  return { mutate, isLoading, error };
}
