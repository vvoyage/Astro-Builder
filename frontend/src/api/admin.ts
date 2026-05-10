import apiClient from './client';

export interface ProjectsByStatus {
  status: string;
  count: number;
}

export interface StatsResponse {
  total_users: number;
  total_projects: number;
  projects_by_status: ProjectsByStatus[];
  total_templates: number;
}

export interface AdminUserItem {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  keycloak_id: string | null;
  project_count: number;
}

export interface AdminProjectMeta {
  id: string;
  name: string;
  status: string;
}

export interface AdminUserDetail {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  keycloak_id: string | null;
  projects: AdminProjectMeta[];
}

export async function getAdminStats(): Promise<StatsResponse> {
  const { data } = await apiClient.get<StatsResponse>('/admin/stats');
  return data;
}

export async function listAdminUsers(skip = 0, limit = 50): Promise<AdminUserItem[]> {
  const { data } = await apiClient.get<AdminUserItem[]>('/admin/users', {
    params: { skip, limit },
  });
  return data;
}

export async function getAdminUser(userId: string): Promise<AdminUserDetail> {
  const { data } = await apiClient.get<AdminUserDetail>(`/admin/users/${userId}`);
  return data;
}

export async function patchAdminUser(
  userId: string,
  payload: { is_active: boolean },
): Promise<AdminUserDetail> {
  const { data } = await apiClient.patch<AdminUserDetail>(`/admin/users/${userId}`, payload);
  return data;
}

export async function deleteAdminUser(userId: string): Promise<void> {
  await apiClient.delete(`/admin/users/${userId}`);
}

// ---------------------------------------------------------------------------
// Templates (admin CRUD)
// ---------------------------------------------------------------------------

export interface AdminTemplate {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  text_prompt: string;
  is_active: boolean;
}

export interface TemplatePayload {
  slug: string;
  name: string;
  text_prompt: string;
  description?: string;
  is_active: boolean;
}

export async function listAllTemplates(): Promise<AdminTemplate[]> {
  const { data } = await apiClient.get<AdminTemplate[]>('/admin/templates');
  return data;
}

export async function createTemplate(payload: TemplatePayload): Promise<AdminTemplate> {
  const { data } = await apiClient.post<AdminTemplate>('/templates/', payload);
  return data;
}

export async function updateTemplate(id: string, payload: TemplatePayload): Promise<AdminTemplate> {
  const { data } = await apiClient.put<AdminTemplate>(`/templates/${id}`, payload);
  return data;
}

export async function deleteTemplate(id: string): Promise<void> {
  await apiClient.delete(`/templates/${id}`);
}
