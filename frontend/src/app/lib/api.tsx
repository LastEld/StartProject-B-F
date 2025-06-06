// frontend/src/app/lib/api.tsx
import {
  SuccessResponse,
  ErrorResponse,
  FastApiError,
  ValidationErrorResponse,
  UserRead,
  UserCreate,
  UserUpdate,
  AuthResponse,
  TokenRefreshRequest,
  ProjectRead,
  ProjectCreate,
  ProjectUpdate,
  ProjectShort,
  ProjectFilters,    // <--- добавить!
  TaskRead,
  TaskCreate,
  TaskUpdate,
  TaskShort,
  TaskFilters,       // <--- уже был!
  DevLogRead,
  DevLogCreate,
  DevLogUpdate,
  DevLogShort,
  PluginRead,
  PluginCreate,
  PluginUpdate,
  PluginShort,
  PluginFilters,     // <--- добавить!
  SettingRead,
  SettingCreate,
  SettingUpdate,
  TemplateRead,
  TemplateCreate,
  TemplateUpdate,
  TemplateShort,
  TemplateFilters,   // <--- добавить!
  TeamRead,
  TeamCreate,
  TeamUpdate,
  TeamFilters,       // <--- добавить!
  AIContextRead,
  AIContextCreate,
  AIContextUpdate,
  ChatMessageRead,
  ChatMessageCreate,
  ChatMessageUpdate,
  ChatMessageShort,
} from './types';
import type { cloneTemplate } from "../lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function getHeaders(token?: string | null) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

type ApiError =
  | ErrorResponse
  | FastApiError
  | ValidationErrorResponse
  | Error;

function parseApiError(errBody: string): ApiError {
  try {
    const errObj = JSON.parse(errBody);
    if (errObj.error) return errObj as ErrorResponse;
    if (errObj.detail) {
      if (typeof errObj.detail === "string") return errObj as FastApiError;
      if (Array.isArray(errObj.detail)) return errObj as ValidationErrorResponse;
    }
    return new Error(JSON.stringify(errObj));
  } catch {
    return new Error(errBody);
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options: {
    method?: "GET" | "POST" | "PATCH" | "DELETE" | "PUT";
    body?: any;
    token?: string | null;
    params?: Record<string, string | number | boolean | string[] | undefined | null>;
  } = {}
): Promise<T> {
  const { method = "GET", body, params } = options;
  let { token } = options;

  const getStoredToken = (): string | null =>
    typeof window !== "undefined" ? localStorage.getItem('access_token') : null;

  if (token === undefined && endpoint !== "/auth/login" && endpoint !== "/auth/refresh") {
    token = getStoredToken();
  }

  let url = `${API_URL}${endpoint}`;
  if (params) {
    const query = new URLSearchParams();
    for (const key in params) {
      const value = params[key];
      if (value !== undefined && value !== null) {
        if (Array.isArray(value)) value.forEach(item => query.append(key, String(item)));
        else query.append(key, String(value));
      }
    }
    const search = query.toString();
    if (search) url += `?${search}`;
  }

  const requestOptions: RequestInit = {
    method,
    headers: getHeaders(token),
  };
  if (body) requestOptions.body = JSON.stringify(body);

  let response = await fetch(url, requestOptions);

  if (response.status === 401 && endpoint !== "/auth/login" && endpoint !== "/auth/refresh") {
    const refreshToken = typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null;
    if (refreshToken) {
      try {
        const refreshRes = await refreshTokenApi({ refresh_token: refreshToken });
        localStorage.setItem('access_token', refreshRes.access_token);
        if (refreshRes.refresh_token) localStorage.setItem('refresh_token', refreshRes.refresh_token);
        requestOptions.headers = getHeaders(refreshRes.access_token);
        response = await fetch(url, requestOptions);
      } catch (e) {
        if (typeof window !== "undefined") {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/auth/login';
        }
        throw new Error("Session expired. Please log in again.");
      }
    } else {
      if (typeof window !== "undefined") {
        localStorage.removeItem('access_token');
        window.location.href = '/auth/login';
      }
      throw new Error("Session expired. Please log in again.");
    }
  }

  if (!response.ok) {
    const errText = await response.text().catch(() => "Unknown error");
    throw parseApiError(errText);
  }

  if (response.status === 204) return {} as T;
  return response.json() as Promise<T>;
}

// --- AUTH ---
export async function loginApi(username: string, password: string): Promise<AuthResponse> {
  const form = new URLSearchParams();
  form.append('username', username);
  form.append('password', password);

  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });

  if (!response.ok) {
    const errText = await response.text().catch(() => "Login failed");
    throw parseApiError(errText);
  }
  return response.json() as Promise<AuthResponse>;
}

export function refreshTokenApi(data: TokenRefreshRequest): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/auth/refresh", { method: "POST", body: data });
}

export function logoutUserApi(token?: string | null): Promise<SuccessResponse> {
  const refreshToken = typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null;
  if (!refreshToken) return Promise.resolve({ result: "No refresh token", detail: "Already logged out or no session." });
  return apiFetch<SuccessResponse>("/auth/logout", {
    method: "POST",
    body: { refresh_token: refreshToken },
    token,
  });
}

export function getMeApi(token?: string | null): Promise<UserRead> {
  return apiFetch<UserRead>("/auth/me", { token });
}

// --- USER ---
export function listUsers(params: Record<string, any> = {}, token?: string | null): Promise<UserRead[]> {
  return apiFetch<UserRead[]>("/users/", { params, token });
}
export function createUser(data: UserCreate, token?: string | null): Promise<UserRead> {
  return apiFetch<UserRead>("/users/", { method: "POST", body: data, token });
}
export function getUser(id: number, token?: string | null): Promise<UserRead> {
  return apiFetch<UserRead>(`/users/${id}`, { token });
}
export function updateUser(id: number, data: UserUpdate, token?: string | null): Promise<UserRead> {
  return apiFetch<UserRead>(`/users/${id}`, { method: "PATCH", body: data, token });
}
export function deleteUser(id: number, token?: string | null): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/users/${id}`, { method: "DELETE", token });
}

// --- PROJECT ---
export function listProjects(params: ProjectFilters = {}, token?: string | null): Promise<ProjectShort[]> {
  return apiFetch<ProjectShort[]>("/projects/", { params, token });
}
export function createProject(data: ProjectCreate, token?: string | null): Promise<ProjectRead> {
  return apiFetch<ProjectRead>("/projects/", { method: "POST", body: data, token });
}
export function getProject(id: number, token?: string | null): Promise<ProjectRead> {
  return apiFetch<ProjectRead>(`/projects/${id}`, { token });
}
export function updateProject(id: number, data: ProjectUpdate, token?: string | null): Promise<ProjectRead> {
  return apiFetch<ProjectRead>(`/projects/${id}`, { method: "PATCH", body: data, token });
}
export function deleteProject(id: number, token?: string | null): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/projects/${id}`, { method: "DELETE", token });
}
export function restoreProject(id: number, token?: string | null): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/projects/${id}/restore`, { method: "POST", token });
}

// --- TASK ---
export function listTasks(params: TaskFilters = {}, token?: string | null): Promise<TaskShort[]> {
  return apiFetch<TaskShort[]>("/tasks/", { params, token });
}
export function getTask(id: number, token?: string | null): Promise<TaskRead> {
  return apiFetch<TaskRead>(`/tasks/${id}`, { token });
}
export function createTask(data: TaskCreate, token?: string | null): Promise<TaskRead> {
  return apiFetch<TaskRead>("/tasks/", { method: "POST", body: data, token });
}
export function updateTask(id: number, data: TaskUpdate, token?: string | null): Promise<TaskRead> {
  return apiFetch<TaskRead>(`/tasks/${id}`, { method: "PATCH", body: data, token });
}
export function deleteTask(id: number, token?: string | null): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/tasks/${id}`, { method: "DELETE", token });
}
export function restoreTask(id: number, token?: string | null): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/tasks/${id}/restore`, { method: "POST", token });
}

// --- DEVLOG ---
export function listDevlogs(params: Record<string, any> = {}, token?: string | null): Promise<DevLogShort[]> {
  return apiFetch<DevLogShort[]>("/devlog/", { params, token });
}
export function createDevlog(data: DevLogCreate, token?: string | null): Promise<DevLogRead> {
  return apiFetch<DevLogRead>("/devlog/", { method: "POST", body: data, token });
}
export function getDevlog(id: number, token?: string | null): Promise<DevLogRead> {
  return apiFetch<DevLogRead>(`/devlog/${id}`, { token });
}
export function updateDevlog(id: number, data: DevLogUpdate, token?: string | null): Promise<DevLogRead> {
  return apiFetch<DevLogRead>(`/devlog/${id}`, { method: "PATCH", body: data, token });
}
export function deleteDevlog(id: number, token?: string | null): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/devlog/${id}`, { method: "DELETE", token });
}
export function restoreDevlog(id: number, token?: string | null): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/devlog/${id}/restore`, { method: "POST", token });
}

// --- PLUGIN ---
export function listPlugins(params: PluginFilters = {}, token?: string | null): Promise<PluginShort[]> {
  return apiFetch<PluginShort[]>("/plugins/", { params, token });
}
export function createPlugin(data: PluginCreate, token?: string | null): Promise<PluginRead> {
  return apiFetch<PluginRead>("/plugins/", { method: "POST", body: data, token });
}
export function getPlugin(id: number, token?: string | null): Promise<PluginRead> {
  return apiFetch<PluginRead>(`/plugins/${id}`, { token });
}
export function updatePlugin(id: number, data: PluginUpdate, token?: string | null): Promise<PluginRead> {
  return apiFetch<PluginRead>(`/plugins/${id}`, { method: "PATCH", body: data, token });
}
export function deletePlugin(id: number, token?: string | null): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/plugins/${id}`, { method: "DELETE", token });
}
export function restorePlugin(id: number, token?: string | null): Promise<PluginRead> {
  return apiFetch<PluginRead>(`/plugins/${id}/restore`, { method: "POST", token });
}

// --- SETTINGS ---
export function listSettings(params: Record<string, any> = {}, token?: string | null): Promise<SettingRead[]> {
  return apiFetch<SettingRead[]>("/settings/", { params, token });
}
export function createSetting(data: SettingCreate, token?: string | null): Promise<SettingRead> {
  return apiFetch<SettingRead>("/settings/", { method: "POST", body: data, token });
}
export function updateSetting(id: number, data: SettingUpdate, token?: string | null): Promise<SettingRead> {
  return apiFetch<SettingRead>(`/settings/${id}`, { method: "PATCH", body: data, token });
}
export function deleteSetting(id: number, token?: string | null): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/settings/${id}`, { method: "DELETE", token });
}

// --- TEMPLATE ---
export function listTemplates(params: TemplateFilters = {}, token?: string | null): Promise<TemplateShort[]> {
  return apiFetch<TemplateShort[]>("/templates/", { params, token });
}
export function createTemplate(data: TemplateCreate, token?: string | null): Promise<TemplateRead> {
  return apiFetch<TemplateRead>("/templates/", { method: "POST", body: data, token });
}
export function getTemplate(id: number, token?: string | null): Promise<TemplateRead> {
  return apiFetch<TemplateRead>(`/templates/${id}`, { token });
}
export function updateTemplate(id: number, data: TemplateUpdate, token?: string | null): Promise<TemplateRead> {
  return apiFetch<TemplateRead>(`/templates/${id}`, { method: "PATCH", body: data, token });
}
export function deleteTemplate(id: number, token?: string | null): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/templates/${id}`, { method: "DELETE", token });
}
export function restoreTemplate(id: number, token?: string | null): Promise<TemplateRead> {
  return apiFetch<TemplateRead>(`/templates/${id}/restore`, { method: "POST", token });
}
export function cloneTemplate(id: number, token?: string | null): Promise<cloneTemplate> {
  return apiFetch<cloneTemplate>(`/templates/${id}/clone`, { method: "POST", token });
}

// --- TEAM ---
export function listTeams(params: TeamFilters = {}, token?: string | null): Promise<TeamRead[]> {
  return apiFetch<TeamRead[]>("/teams/", { params, token });
}
export function createTeam(data: TeamCreate, token?: string | null): Promise<TeamRead> {
  return apiFetch<TeamRead>("/teams/", { method: "POST", body: data, token });
}
export function getTeam(id: number, token?: string | null): Promise<TeamRead> {
  return apiFetch<TeamRead>(`/teams/${id}`, { token });
}
export function updateTeam(id: number, data: TeamUpdate, token?: string | null): Promise<TeamRead> {
  return apiFetch<TeamRead>(`/teams/${id}`, { method: "PATCH", body: data, token });
}
export function deleteTeam(id: number, token?: string | null): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/teams/${id}`, { method: "DELETE", token });
}

// --- AI CONTEXT ---
export function listAIContexts(params: Record<string, any> = {}, token?: string | null): Promise<AIContextRead[]> {
  return apiFetch<AIContextRead[]>("/ai_context/", { params, token });
}
export function createAIContext(data: AIContextCreate, token?: string | null): Promise<AIContextRead> {
  return apiFetch<AIContextRead>("/ai_context/", { method: "POST", body: data, token });
}
export function getAIContext(id: number, token?: string | null): Promise<AIContextRead> {
  return apiFetch<AIContextRead>(`/ai_context/${id}`, { token });
}
export function updateAIContext(id: number, data: AIContextUpdate, token?: string | null): Promise<AIContextRead> {
  return apiFetch<AIContextRead>(`/ai_context/${id}`, { method: "PATCH", body: data, token });
}
export function deleteAIContext(id: number, token?: string | null): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/ai_context/${id}`, { method: "DELETE", token });
}

// --- JARVIS CHAT ---
export function listChatMessages(params: Record<string, any> = {}, token?: string | null): Promise<ChatMessageShort[]> {
  return apiFetch<ChatMessageShort[]>("/jarvis/chat/", { params, token });
}
export function createChatMessage(data: ChatMessageCreate, token?: string | null): Promise<ChatMessageRead> {
  return apiFetch<ChatMessageRead>("/jarvis/chat/", { method: "POST", body: data, token });
}
export function getChatMessage(id: number, token?: string | null): Promise<ChatMessageRead> {
  return apiFetch<ChatMessageRead>(`/jarvis/chat/${id}`, { token });
}
export function updateChatMessage(id: number, data: ChatMessageUpdate, token?: string | null): Promise<ChatMessageRead> {
  return apiFetch<ChatMessageRead>(`/jarvis/chat/${id}`, { method: "PATCH", body: data, token });
}
export function deleteChatMessage(id: number, token?: string | null): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/jarvis/chat/${id}`, { method: "DELETE", token });
}
