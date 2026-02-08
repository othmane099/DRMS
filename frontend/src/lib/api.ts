import {
  User,
  UserCreateInput,
  UserUpdateInput,
  UserPermissionsResponse,
  RoleWithPermissions,
  RoleCreateInput,
  RoleUpdateInput,
  Permission,
  LoggedHistory,
  PaginatedResponse,
  LoginResponse,
  ApiError,
  UserFilters,
  ActivityFilters,
  BulkAction,
  Role,
  Stage,
  StageCreateInput,
  StageUpdateInput,
  StageFilters,
  Category,
  CategoryCreateInput,
  CategoryUpdateInput,
  CategoryFilters,
  Subcategory,
  SubcategoryCreateInput,
  SubcategoryUpdateInput,
  SubcategoryFilters,
  Tag,
  TagCreateInput,
  TagUpdateInput,
  TagFilters,
  Document,
  DocumentCreateInput,
  DocumentUpdateInput,
  DocumentFilters,
  DocumentVersion,
  VersionHistoryResponse,
  DocumentHistoryFilters,
  PaginatedDocumentHistoryResponse,
  DocumentComment,
  DocumentCommentCreateInput,
  SharedUser,
  ShareDocumentInput,
  ShareLinkInput,
  ShareLinkResponse,
  DocumentReminder,
  DashboardResponse, UserBasicId,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      (headers as Record<string, string>)['X-Session-Key'] = token;
    }

    console.log('API Request:', endpoint);
    console.log('Token:', token);
    console.log('Headers:', headers);

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      if (response.status === 401) {
        // Clear session and redirect to login (but only if not already on login page)
        localStorage.removeItem('token');
        localStorage.removeItem('user');

        // Only redirect if we're not already on the login page
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }

        const error: ApiError = await response.json().catch(() => ({
          detail: 'Session expired',
        }));
        error.status = response.status;
        throw error;
      }

      const error: ApiError = await response.json().catch(() => ({
        detail: 'An error occurred',
      }));
      error.status = response.status;
      throw error;
    }

    // Handle empty responses
    const text = await response.text();
    if (!text) return {} as T;
    return JSON.parse(text);
  }

  // Auth endpoints
  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>('/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    console.log('Raw login response:', response);
    return response;
  }

  async logout(): Promise<void> {
    await this.request('/logout', { method: 'POST' });
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }

  // User endpoints
  async getUsers(filters?: UserFilters): Promise<PaginatedResponse<User>> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.search) params.set('search', filters.search);
      if (filters.role_id) params.set('role_id', String(filters.role_id));
      if (filters.active !== undefined) params.set('active', String(filters.active));
      if (filters.page) params.set('page', String(filters.page));
      if (filters.page_size) params.set('page_size', String(filters.page_size));
    }
    const query = params.toString();
    return this.request<PaginatedResponse<User>>(
      `/api/v1/users${query ? `?${query}` : ''}`
    );
  }

  async getUsersForAssignment(): Promise<UserBasicId[]> {
    return this.request<UserBasicId[]>(`/api/v1/users/for-assignment`);
  }

  async getUser(id: string): Promise<User> {
    return this.request<User>(`/api/v1/users/${id}`);
  }

  async createUser(data: UserCreateInput): Promise<User> {
    return this.request<User>('/api/v1/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateUser(id: string, data: UserUpdateInput): Promise<User> {
    return this.request<User>(`/api/v1/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteUser(id: string): Promise<void> {
    await this.request(`/api/v1/users/${id}`, { method: 'DELETE' });
  }

  async updateUserStatus(id: string, isActive: boolean): Promise<User> {
    return this.request<User>(`/api/v1/users/${id}/status`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: isActive }),
    });
  }

  async assignUserRole(id: string, roleId: string | null): Promise<User> {
    return this.request<User>(`/api/v1/users/${id}/role`, {
      method: 'PUT',
      body: JSON.stringify({ role_id: roleId }),
    });
  }

  async updateUserPermissions(id: string, permissions: string[]): Promise<UserPermissionsResponse> {
    return this.request<UserPermissionsResponse>(`/api/v1/users/${id}/permissions`, {
      method: 'PATCH',
      body: JSON.stringify({ permissions }),
    });
  }

  async bulkUserAction(action: BulkAction): Promise<{ affected: number }> {
    return this.request<{ affected: number }>('/api/v1/users/bulk-action', {
      method: 'POST',
      body: JSON.stringify(action),
    });
  }

  // Role endpoints
  async getRoles(): Promise<Role[]> {
    return this.request<Role[]>('/api/v1/roles');
  }

  async getRole(id: string): Promise<RoleWithPermissions> {
    return this.request<RoleWithPermissions>(`/api/v1/roles/${id}`);
  }

  async createRole(data: RoleCreateInput): Promise<RoleWithPermissions> {
    return this.request<RoleWithPermissions>('/api/v1/roles', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateRole(id: string, data: RoleUpdateInput): Promise<RoleWithPermissions> {
    return this.request<RoleWithPermissions>(`/api/v1/roles/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteRole(id: string): Promise<void> {
    await this.request(`/api/v1/roles/${id}`, { method: 'DELETE' });
  }

  async updateRoleStatus(id: string, isActive: boolean): Promise<Role> {
    return this.request<Role>(`/api/v1/roles/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active: isActive }),
    });
  }

  // Permission endpoints
  async getPermissions(): Promise<Permission[]> {
    return this.request<Permission[]>('/api/v1/permissions');
  }

  // Activity log endpoints
  async getActivityLogs(filters?: ActivityFilters): Promise<PaginatedResponse<LoggedHistory>> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.user_id) params.set('user_id', filters.user_id);
      if (filters.type) params.set('type', filters.type);
      if (filters.date_from) params.set('date_from', filters.date_from);
      if (filters.date_to) params.set('date_to', filters.date_to);
      if (filters.search) params.set('search', filters.search);
      if (filters.page) params.set('page', String(filters.page));
      if (filters.page_size) params.set('page_size', String(filters.page_size));
    }
    const query = params.toString();
    return this.request<PaginatedResponse<LoggedHistory>>(
      `/api/v1/logged-history${query ? `?${query}` : ''}`
    );
  }

  // Stage endpoints
  async getStages(filters?: StageFilters): Promise<PaginatedResponse<Stage>> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.search) params.set('search', filters.search);
      if (filters.page) params.set('page', String(filters.page));
      if (filters.page_size) params.set('page_size', String(filters.page_size));
    }
    const query = params.toString();
    return this.request<PaginatedResponse<Stage>>(
      `/api/v1/stages${query ? `?${query}` : ''}`
    );
  }

  async getStage(id: string): Promise<Stage> {
    return this.request<Stage>(`/api/v1/stages/${id}`);
  }

  async createStage(data: StageCreateInput): Promise<Stage> {
    return this.request<Stage>('/api/v1/stages', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateStage(id: string, data: StageUpdateInput): Promise<Stage> {
    return this.request<Stage>(`/api/v1/stages/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteStage(id: string): Promise<void> {
    await this.request(`/api/v1/stages/${id}`, { method: 'DELETE' });
  }

  // Category endpoints
  async getCategories(filters?: CategoryFilters): Promise<PaginatedResponse<Category>> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.search) params.set('search', filters.search);
      if (filters.page) params.set('page', String(filters.page));
      if (filters.page_size) params.set('page_size', String(filters.page_size));
    }
    const query = params.toString();
    return this.request<PaginatedResponse<Category>>(
      `/api/v1/categories${query ? `?${query}` : ''}`
    );
  }

  async getCategory(id: string): Promise<Category> {
    return this.request<Category>(`/api/v1/categories/${id}`);
  }

  async createCategory(data: CategoryCreateInput): Promise<Category> {
    return this.request<Category>('/api/v1/categories', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateCategory(id: string, data: CategoryUpdateInput): Promise<Category> {
    return this.request<Category>(`/api/v1/categories/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteCategory(id: string): Promise<void> {
    await this.request(`/api/v1/categories/${id}`, { method: 'DELETE' });
  }

  // Subcategory endpoints
  async getSubcategories(filters?: SubcategoryFilters): Promise<PaginatedResponse<Subcategory>> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.category_id) params.set('category_id', filters.category_id);
      if (filters.search) params.set('search', filters.search);
      if (filters.page) params.set('page', String(filters.page));
      if (filters.page_size) params.set('page_size', String(filters.page_size));
    }
    const query = params.toString();
    return this.request<PaginatedResponse<Subcategory>>(
      `/api/v1/subcategories${query ? `?${query}` : ''}`
    );
  }

  async getSubcategory(id: string): Promise<Subcategory> {
    return this.request<Subcategory>(`/api/v1/subcategories/${id}`);
  }

  async createSubcategory(data: SubcategoryCreateInput): Promise<Subcategory> {
    return this.request<Subcategory>('/api/v1/subcategories', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateSubcategory(id: string, data: SubcategoryUpdateInput): Promise<Subcategory> {
    return this.request<Subcategory>(`/api/v1/subcategories/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteSubcategory(id: string): Promise<void> {
    await this.request(`/api/v1/subcategories/${id}`, { method: 'DELETE' });
  }

  // Tag endpoints
  async getTags(filters?: TagFilters): Promise<PaginatedResponse<Tag>> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.search) params.set('search', filters.search);
      if (filters.page) params.set('page', String(filters.page));
      if (filters.page_size) params.set('page_size', String(filters.page_size));
    }
    const query = params.toString();
    return this.request<PaginatedResponse<Tag>>(
      `/api/v1/tags${query ? `?${query}` : ''}`
    );
  }

  async getTag(id: string): Promise<Tag> {
    return this.request<Tag>(`/api/v1/tags/${id}`);
  }

  async createTag(data: TagCreateInput): Promise<Tag> {
    return this.request<Tag>('/api/v1/tags', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateTag(id: string, data: TagUpdateInput): Promise<Tag> {
    return this.request<Tag>(`/api/v1/tags/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteTag(id: string): Promise<void> {
    await this.request(`/api/v1/tags/${id}`, { method: 'DELETE' });
  }

  // Document endpoints
  async getDocuments(filters?: DocumentFilters): Promise<PaginatedResponse<Document>> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.category_id) params.set('category_id', filters.category_id);
      if (filters.stage_id) params.set('stage_id', filters.stage_id);
      if (filters.created_date) params.set('created_date', filters.created_date);
      if (filters.search) params.set('search', filters.search);
      if (filters.archive !== undefined) params.set('archive', String(filters.archive));
      if (filters.page) params.set('page', String(filters.page));
      if (filters.page_size) params.set('page_size', String(filters.page_size));
    }
    const query = params.toString();
    return this.request<PaginatedResponse<Document>>(
      `/api/v1/documents${query ? `?${query}` : ''}`
    );
  }

  async getDocument(id: string): Promise<Document> {
    return this.request<Document>(`/api/v1/documents/${id}`);
  }

  async createDocument(data: DocumentCreateInput): Promise<Document> {
    const formData = new FormData();
    formData.append('name', data.name);
    formData.append('category_id', data.category_id);
    formData.append('subcategory_id', data.subcategory_id);
    formData.append('stage_id', data.stage_id);
    formData.append('assigned_to', data.assigned_to);
    formData.append('document', data.document);
    if (data.description) formData.append('description', data.description);
    if (data.tag_ids && data.tag_ids.length > 0) {
      formData.append('tags', data.tag_ids.join(','));
    }

    const token = this.getToken();
    const headers: HeadersInit = {};
    if (token) {
      (headers as Record<string, string>)['X-Session-Key'] = token;
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/documents`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
        const error: ApiError = await response.json().catch(() => ({
          detail: 'Session expired',
        }));
        error.status = response.status;
        throw error;
      }

      const error: ApiError = await response.json().catch(() => ({
        detail: 'An error occurred',
      }));
      error.status = response.status;
      throw error;
    }

    return response.json();
  }

  async updateDocument(id: string, data: DocumentUpdateInput): Promise<Document> {
    return this.request<Document>(`/api/v1/documents/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteDocument(id: string): Promise<void> {
    await this.request(`/api/v1/documents/${id}`, { method: 'DELETE' });
  }

  async archiveDocument(id: string): Promise<Document> {
    return this.request<Document>(`/api/v1/documents/${id}/archive`, {
      method: 'PATCH',
    });
  }

  // My document endpoints
  async getMyDocuments(filters?: DocumentFilters): Promise<PaginatedResponse<Document>> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.category_id) params.set('category_id', filters.category_id);
      if (filters.stage_id) params.set('stage_id', filters.stage_id);
      if (filters.created_date) params.set('created_date', filters.created_date);
      if (filters.search) params.set('search', filters.search);
      if (filters.archive !== undefined) params.set('archive', String(filters.archive));
      if (filters.page) params.set('page', String(filters.page));
      if (filters.page_size) params.set('page_size', String(filters.page_size));
    }
    const query = params.toString();
    return this.request<PaginatedResponse<Document>>(
      `/api/v1/documents/me${query ? `?${query}` : ''}`
    );
  }

  async getMyDocument(id: string): Promise<Document> {
    return this.request<Document>(`/api/v1/documents/${id}/me`);
  }

  async updateMyDocument(id: string, data: DocumentUpdateInput): Promise<Document> {
    return this.request<Document>(`/api/v1/documents/${id}/me`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteMyDocument(id: string): Promise<void> {
    await this.request(`/api/v1/documents/${id}/me`, { method: 'DELETE' });
  }

  async archiveMyDocument(id: string): Promise<Document> {
    return this.request<Document>(`/api/v1/documents/${id}/archive/me`, {
      method: 'PATCH',
    });
  }

  async downloadMyDocument(id: string): Promise<void> {
    const token = this.getToken();
    const headers: HeadersInit = {};
    if (token) {
      (headers as Record<string, string>)['X-Session-Key'] = token;
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${id}/download/me`, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
        throw new Error('Session expired');
      }
      throw new Error('Failed to download document');
    }

    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = 'document';
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename\*?=['"]?(?:UTF-8'')?([^'"\n;]+)['"]?/i);
      if (filenameMatch && filenameMatch[1]) {
        filename = decodeURIComponent(filenameMatch[1]);
      }
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  async getMyDocumentVersions(id: string): Promise<DocumentVersion[]> {
    return this.request<DocumentVersion[]>(`/api/v1/documents/${id}/versions/me`);
  }

  async downloadMyDocumentVersion(documentId: string, versionId: string): Promise<void> {
    const token = this.getToken();
    const headers: HeadersInit = {};
    if (token) {
      (headers as Record<string, string>)['X-Session-Key'] = token;
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}/versions/${versionId}/download/me`, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
        throw new Error('Session expired');
      }
      throw new Error('Failed to download document version');
    }

    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = 'document';
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename\*?=['"]?(?:UTF-8'')?([^'"\n;]+)['"]?/i);
      if (filenameMatch && filenameMatch[1]) {
        filename = decodeURIComponent(filenameMatch[1]);
      }
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  async getMyDocumentComments(id: string): Promise<DocumentComment[]> {
    return this.request<DocumentComment[]>(`/api/v1/documents/${id}/comments/me`);
  }

  async createMyDocumentComment(documentId: string, data: DocumentCommentCreateInput): Promise<DocumentComment> {
    return this.request<DocumentComment>(`/api/v1/documents/${documentId}/comments/me`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getMySharedUsers(documentId: string): Promise<SharedUser[]> {
    return this.request<SharedUser[]>(`/api/v1/documents/${documentId}/shared-users/me`);
  }

  async shareMyDocument(documentId: string, data: ShareDocumentInput): Promise<SharedUser[]> {
    return this.request<SharedUser[]>(`/api/v1/documents/${documentId}/share/me`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteMyShare(documentId: string, shareId: string): Promise<{ detail: string }> {
    return this.request<{ detail: string }>(`/api/v1/documents/${documentId}/shares/${shareId}/me`, {
      method: 'DELETE',
    });
  }

  async generateMyShareLink(documentId: string, data: ShareLinkInput): Promise<ShareLinkResponse> {
    return this.request<ShareLinkResponse>(`/api/v1/documents/${documentId}/share-link/me`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getMyDocumentReminders(documentId: string): Promise<DocumentReminder[]> {
    return this.request<DocumentReminder[]>(`/api/v1/documents/${documentId}/reminders/me`);
  }

  async createMyDocumentReminder(
    documentId: string,
    data: {
      date: string;
      time: string;
      subject: string;
      message: string;
      assign_user: string[];
    }
  ): Promise<DocumentReminder> {
    return this.request<DocumentReminder>(`/api/v1/documents/${documentId}/reminders/me`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getMyReminder(reminderId: string): Promise<DocumentReminder> {
    return this.request<DocumentReminder>(`/api/v1/reminders/${reminderId}/me`);
  }

  async updateMyReminder(
    reminderId: string,
    data: {
      date: string;
      time: string;
      subject: string;
      message: string;
      assign_user: string[];
    }
  ): Promise<DocumentReminder> {
    return this.request<DocumentReminder>(`/api/v1/reminders/${reminderId}/me`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteMyReminder(reminderId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/reminders/${reminderId}/me`, {
      method: 'DELETE',
    });
  }

  async downloadDocument(id: string): Promise<void> {
    const token = this.getToken();
    const headers: HeadersInit = {};
    if (token) {
      (headers as Record<string, string>)['X-Session-Key'] = token;
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${id}/download`, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
        throw new Error('Session expired');
      }
      throw new Error('Failed to download document');
    }

    // Get filename from Content-Disposition header or use a default
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = 'document';
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename\*?=['"]?(?:UTF-8'')?([^'"\n;]+)['"]?/i);
      if (filenameMatch && filenameMatch[1]) {
        filename = decodeURIComponent(filenameMatch[1]);
      }
    }

    // Create blob and trigger download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  async getDocumentVersions(id: string): Promise<DocumentVersion[]> {
    return this.request<DocumentVersion[]>(`/api/v1/documents/${id}/versions`);
  }

  async downloadDocumentVersion(documentId: string, versionId: string): Promise<void> {
    const token = this.getToken();
    const headers: HeadersInit = {};
    if (token) {
      (headers as Record<string, string>)['X-Session-Key'] = token;
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}/versions/${versionId}/download`, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
        throw new Error('Session expired');
      }
      throw new Error('Failed to download document version');
    }

    // Get filename from Content-Disposition header or use a default
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = 'document';
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename\*?=['"]?(?:UTF-8'')?([^'"\n;]+)['"]?/i);
      if (filenameMatch && filenameMatch[1]) {
        filename = decodeURIComponent(filenameMatch[1]);
      }
    }

    // Create blob and trigger download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  async createDocumentVersion(documentId: string, file: File): Promise<VersionHistoryResponse> {
    const formData = new FormData();
    formData.append('document', file);

    const token = this.getToken();
    const headers: HeadersInit = {};
    if (token) {
      (headers as Record<string, string>)['X-Session-Key'] = token;
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}/versions`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
        const error: ApiError = await response.json().catch(() => ({
          detail: 'Session expired',
        }));
        error.status = response.status;
        throw error;
      }

      const error: ApiError = await response.json().catch(() => ({
        detail: 'An error occurred',
      }));
      error.status = response.status;
      throw error;
    }

    return response.json();
  }
  async createMyDocumentVersion(documentId: string, file: File): Promise<VersionHistoryResponse> {
    const formData = new FormData();
    formData.append('document', file);

    const token = this.getToken();
    const headers: HeadersInit = {};
    if (token) {
      (headers as Record<string, string>)['X-Session-Key'] = token;
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}/versions/me`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
        const error: ApiError = await response.json().catch(() => ({
          detail: 'Session expired',
        }));
        error.status = response.status;
        throw error;
      }

      const error: ApiError = await response.json().catch(() => ({
        detail: 'An error occurred',
      }));
      error.status = response.status;
      throw error;
    }

    return response.json();
  }

  async getDocumentHistories(filters?: DocumentHistoryFilters): Promise<PaginatedDocumentHistoryResponse> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.search) params.set('search', filters.search);
      if (filters.page) params.set('page', String(filters.page));
      if (filters.page_size) params.set('page_size', String(filters.page_size));
    }

    const query = params.toString();
    return this.request<PaginatedDocumentHistoryResponse>(
      `/api/v1/histories${query ? `?${query}` : ''}`
    );
  }

  async getMyDocumentHistories(filters?: DocumentHistoryFilters): Promise<PaginatedDocumentHistoryResponse> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.search) params.set('search', filters.search);
      if (filters.page) params.set('page', String(filters.page));
      if (filters.page_size) params.set('page_size', String(filters.page_size));
    }

    const query = params.toString();
    return this.request<PaginatedDocumentHistoryResponse>(
        `/api/v1/histories/me${query ? `?${query}` : ''}`
    );
  }

  async getDocumentComments(id: string): Promise<DocumentComment[]> {
    return this.request<DocumentComment[]>(`/api/v1/documents/${id}/comments`);
  }

  async createDocumentComment(documentId: string, data: DocumentCommentCreateInput): Promise<DocumentComment> {
    return this.request<DocumentComment>(`/api/v1/documents/${documentId}/comments`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getSharedUsers(documentId: string): Promise<SharedUser[]> {
    return this.request<SharedUser[]>(`/api/v1/documents/${documentId}/shared-users`);
  }

  async shareDocument(documentId: string, data: ShareDocumentInput): Promise<SharedUser[]> {
    return this.request<SharedUser[]>(`/api/v1/documents/${documentId}/share`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteShare(documentId: string, shareId: string): Promise<{ detail: string }> {
    return this.request<{ detail: string }>(`/api/v1/documents/${documentId}/share/${shareId}`, {
      method: 'DELETE',
    });
  }

  async generateShareLink(documentId: string, data: ShareLinkInput): Promise<ShareLinkResponse> {
    return this.request<ShareLinkResponse>(`/api/v1/documents/${documentId}/share-link`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async previewSharedDocument(token: string, password?: string): Promise<Blob> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    const body = password ? JSON.stringify({ password }) : JSON.stringify({});

    const response = await fetch(`${API_BASE_URL}/api/v1/documents/shared/${token}`, {
      method: 'POST',
      headers,
      body,
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: 'Failed to preview document',
      }));
      error.status = response.status;
      throw error;
    }

    // Create a blob with the content type from the response
    const contentType = response.headers.get('Content-Type') || 'application/octet-stream';
    const blob = await response.blob();

    // Return a new blob with the correct type if needed
    return new Blob([blob], { type: contentType });
  }

  async getDocumentReminders(documentId: string): Promise<DocumentReminder[]> {
    return this.request<DocumentReminder[]>(`/api/v1/documents/${documentId}/reminders`);
  }

  async getReminders(filters?: {
    page?: number;
    page_size?: number;
    document_id?: string;
  }): Promise<PaginatedResponse<DocumentReminder>> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.page) params.set('page', String(filters.page));
      if (filters.page_size) params.set('page_size', String(filters.page_size));
      if (filters.document_id) params.set('document_id', filters.document_id);
    }
    const query = params.toString();
    return this.request<PaginatedResponse<DocumentReminder>>(
      `/api/v1/reminders${query ? `?${query}` : ''}`
    );
  }

  async getMyReminders(filters?: {
    page?: number;
    page_size?: number;
    document_id?: string;
  }): Promise<PaginatedResponse<DocumentReminder>> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.page) params.set('page', String(filters.page));
      if (filters.page_size) params.set('page_size', String(filters.page_size));
      if (filters.document_id) params.set('document_id', filters.document_id);
    }
    const query = params.toString();
    return this.request<PaginatedResponse<DocumentReminder>>(
        `/api/v1/reminders/me${query ? `?${query}` : ''}`
    );
  }

  async getReminder(reminderId: string): Promise<DocumentReminder> {
    return this.request<DocumentReminder>(`/api/v1/reminders/${reminderId}`);
  }

  async createDocumentReminder(
    documentId: string,
    data: {
      date: string;
      time: string;
      subject: string;
      message: string;
      assign_user: string[];
    }
  ): Promise<DocumentReminder> {
    return this.request<DocumentReminder>(`/api/v1/documents/${documentId}/reminders`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateReminder(
    reminderId: string,
    data: {
      date: string;
      time: string;
      subject: string;
      message: string;
      assign_user: string[];
    }
  ): Promise<DocumentReminder> {
    return this.request<DocumentReminder>(`/api/v1/reminders/${reminderId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteReminder(reminderId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/reminders/${reminderId}`, {
      method: 'DELETE',
    });
  }

  // Dashboard endpoint
  async getDashboard(filters?: {
    reminder_start_date?: string;
    reminder_end_date?: string;
  }): Promise<DashboardResponse> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.reminder_start_date) params.set('reminder_start_date', filters.reminder_start_date);
      if (filters.reminder_end_date) params.set('reminder_end_date', filters.reminder_end_date);
    }
    const query = params.toString();
    return this.request<DashboardResponse>(`/api/v1/dashboard${query ? `?${query}` : ''}`);
  }
}

export const api = new ApiClient();
