// Common types
export interface Message {
  detail: string;
}
// User types
export interface User {
  id: string; // UUID
  username: string;
  email: string | null;
  phone: string | null;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_superuser?: boolean;
  last_login?: string;
  role?: RoleWithPermissions | null;
  custom_permissions?: (Permission | string)[]; // Can be array of Permission objects or permission code strings
  created_at?: string;
  updated_at?: string;
}

export interface UserBasicId {
  id: string; // UUID
  username: string;
}

export interface UserCreateInput {
  username: string;
  email?: string;
  password: string;
  first_name: string;
  last_name: string;
  phone?: string;
  role_id?: string; // UUID
  is_active?: boolean;
}

export interface UserUpdateInput {
  username?: string;
  email?: string;
  password?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  is_active?: boolean;
  role_id?: string; // UUID
}

// Role types
export interface Role {
  id: string; // UUID
  name: string;
  description: string;
  permission_count?: number;
  user_count?: number;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface RoleWithPermissions {
  id: string; // UUID
  name: string;
  description: string;
  permissions: (Permission | string)[]; // Can be array of Permission objects or permission code strings
  user_count?: number;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface RoleCreateInput {
  name: string;
  description: string;
  permissions: string[];
}

export interface RoleUpdateInput {
  name?: string;
  description?: string;
  permissions?: string[];
}

export interface RoleStatusUpdate {
  is_active: boolean;
}

// Permission types
export interface Permission {
  id: string;
  name: string;
  code: string;
  description?: string;
  is_active?: boolean;
}

export interface UserPermissionsResponse {
  id: string;
  username: string;
  role_permissions: Permission[];
  custom_permissions: Permission[];
}

// Stage types
export interface Stage {
  id: string; // UUID
  title: string;
  color: string | null;
  created_at: string;
  updated_at?: string;
}

export interface StageCreateInput {
  title: string;
  color?: string;
}

export interface StageUpdateInput {
  title?: string;
  color?: string;
}

// Activity log types
export interface LoggedHistory {
  id: number;
  user_id: string;
  user?: User;
  user_name?: string;
  type: string; // login, logout, create, edit, delete, view
  details: Record<string, any> | null;
  ip: string | null;
  date: string | null;
  created_at: string;
  updated_at?: string;
}

// API response types
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages?: number;
}

export interface LoginResponse {
  token: string;
  user: User;
  expires_in: number;
}

export interface ApiError {
  detail: string;
  status?: number;
}

// Filter types
export interface UserFilters {
  search?: string;
  role_id?: string; // UUID
  active?: string;
  page?: number;
  page_size?: number;
}

export interface ActivityFilters {
  user_id?: string;
  type?: string; // action type: login, logout, create, edit, delete, view
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface StageFilters {
  search?: string;
  page?: number;
  page_size?: number;
}

// Subcategory types
export interface Subcategory {
  id: string; // UUID
  title: string;
  category_id: string;
  category_title?: string;
  created_at: string;
  updated_at?: string;
}

export interface SubcategoryCreateInput {
  title: string;
  category_id: string;
}

export interface SubcategoryUpdateInput {
  title?: string;
  category_id?: string;
}

export interface SubcategoryFilters {
  category_id?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface BasicSubcategory {
  title: string;
}

// Category types
export interface Category {
  id: string; // UUID
  title: string;
  subcategory_count?: number;
  subcategories?: BasicSubcategory[];
  created_at: string;
  updated_at?: string;
}

export interface CategoryCreateInput {
  title: string;
}

export interface CategoryUpdateInput {
  title?: string;
}

export interface CategoryFilters {
  search?: string;
  page?: number;
  page_size?: number;
}

// Tag types
export interface Tag {
  id: string; // UUID
  title: string;
  created_at: string;
}

export interface TagCreateInput {
  title: string;
}

export interface TagUpdateInput {
  title?: string;
}

export interface TagFilters {
  search?: string;
  page?: number;
  page_size?: number;
}

// Bulk action types
export interface BulkAction {
  user_ids: string[];
  action: 'activate' | 'deactivate' | 'delete' | 'assign_role';
  parameters?: {
    role_id?: string; // UUID
  };
}

export interface PasswordUpdate {
  current_password: string;
  new_password: string;
}

// Document types
export interface Document {
  id: string; // UUID
  name: string;
  category_id: string | null;
  subcategory_id: string | null;
  stage_id: string | null;
  assigned_to: string | null;
  description: string | null;
  created_by: string;
  archive: boolean;
  stage?: {
    title: string;
    color?: string | null;
  };
  assigned_user?: {
    username: string;
  };
  creator?: {
    username: string;
  };
  category?: {
    title: string;
  };
  subcategory?: {
    title: string;
  };
  tags: Tag[];
  created_at: string;
  updated_at?: string;
}

export interface DocumentCreateInput {
  name: string;
  category_id: string;
  subcategory_id: string;
  stage_id: string;
  assigned_to: string;
  document: File;
  description?: string;
  tag_ids?: string[];
}

export interface DocumentUpdateInput {
  name: string;
  category_id: string;
  subcategory_id: string;
  stage_id: string;
  assigned_to: string;
  description?: string;
  tag_ids?: string[];
}

export interface DocumentSearchResponse {
  message: string;
}

export interface DocumentFilters {
  category_id?: string;
  stage_id?: string;
  created_date?: string;
  search?: string;
  archive?: boolean;
  page?: number;
  page_size?: number;
}

// Document Version types
export interface DocumentVersion {
  id: string; // UUID
  document_id: string; // UUID
  document_file: string;
  version_number: number;
  is_current: boolean;
  created_by: string; // UUID
  created_at: string;
  creator?: {
    username: string;
  };
}

export interface VersionHistoryResponse {
  id: string; // UUID
  document_id: string; // UUID
  document_file: string;
  version_number: number;
  is_current: boolean;
  created_by: string; // UUID
  created_at: string;
  creator?: {
    username: string;
  };
}

// Document History types
export interface DocumentHistory {
  id: string; // UUID
  document_id: string | null; // UUID
  action: string;
  description: string;
  created_by: string; // UUID
  created_at: string;
  document?: {
    name: string;
  } | null;
  creator: {
    username: string;
  };
}

export interface DocumentHistoryFilters {
  search?: string;
  page?: number;
  page_size?: number;
}

export interface PaginatedDocumentHistoryResponse {
  data: DocumentHistory[];
  current_page: number;
  total_pages: number;
  total_rows: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
}

// Document Comment types
export interface DocumentComment {
  id: string; // UUID
  document_id: string; // UUID
  user_id: string; // UUID
  comment: string;
  created_at: string;
  updated_at: string;
  user: {
    username: string;
  };
}

export interface DocumentCommentCreateInput {
  comment: string;
}

// Document Share types
export interface SharedUser {
  id: string; // UUID
  document_id: string; // UUID
  user_id: string; // UUID
  start_date: string | null;
  end_date: string | null;
  created_at: string;
  updated_at: string | null;
  user: {
    username: string;
  };
}

export interface ShareDocumentInput {
  user_ids: string[];
  start_date?: string;
  end_date?: string;
}

// Document Share Link types
export interface ShareLinkInput {
  expiration_date?: string;
  password?: string;
}

export interface ShareLinkResponse {
  token: string;
}

// Dashboard types
export interface DashboardCategoryCount {
  category: string;
  count: number;
}

export interface DashboardSubcategoryCount {
  subcategory: string;
  count: number;
}

export interface DashboardReminder {
  id: string;
  title: string;
  start: string;
  time: string;
}

export interface DashboardResponse {
  total_user: number;
  my_total_document: number;
  total_document: number;
  my_today_document: number;
  today_document: number;
  total_category: number;
  my_total_reminder: number;
  total_reminder: number;
  my_today_reminder: number;
  today_reminder: number;
  document_by_category: DashboardCategoryCount[];
  document_by_subcategory: DashboardSubcategoryCount[];
  my_reminders: DashboardReminder[];
  reminders: DashboardReminder[];
}

// Document Reminder types
export interface DocumentReminder {
  id: string; // UUID
  document_id: string; // UUID
  date: string;
  time: string;
  subject: string;
  message: string;
  created_by: string; // UUID
  created_at: string;
  updated_at: string | null;
  creator: {
    username: string;
  };
  document: {
    name: string;
  };
  assigned_users: Array<{
    username: string;
  }>;
}
