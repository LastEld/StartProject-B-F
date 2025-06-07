// frontend/src/app/lib/types.ts
// --- Error/Exception types (generated from backend exceptions.py + FastAPI standard) ---

/**
 * Стандартная FastAPI ошибка: {"detail": "..."} или {"detail": [{"loc": ...,"msg": ...,"type": ...}, ...]}
 */
export type FastApiError =
  | { detail: string }
  | { detail: { loc: any[]; msg: string; type: string }[] };

/**
 * Базовая структура кастомных ошибок (все твои кастомные exception наследуют BaseAppException)
 * 
 * Backend формат: {"error": {"code": "some_code", "message": "Что-то пошло не так", "details": {...}}}
 */
export interface ErrorDetail {
  code: string;      // например, "not_found", "validation_error"
  message: string;   // описание ошибки
  details?: any;     // доп. информация для UI (например, {"field": "email"})
}

export interface ErrorResponse {
  error: ErrorDetail;
}

/**
 * Валидационные ошибки FastAPI (422 Unprocessable Entity)
 */
export interface ValidationErrorDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ValidationErrorResponse {
  detail: ValidationErrorDetail[];
}

/**
 * NotFound error (404)
 */
export interface NotFoundErrorResponse {
  error: {
    code: "not_found";
    message: string;
    details?: any;
  };
}

/**
 * Пример использования:
 * try {
 *   await apiFetch(...);
 * } catch (err) {
 *   // err: Error | ErrorResponse | ValidationErrorResponse
 *   // если err.detail — валидация; если err.error — кастомная ошибка
 * }
 */


// --- Общие типы (универсальные API-ответы) ---
export interface SuccessResponse {
  result: any;
  detail?: string | null;
}

export interface ListResponse<T> {
  results: T[];
  total_count?: number;
  detail?: string;
}

export interface SimpleMessage {
  message: string;
}

// --- User ---
export interface UserBase {
  username: string;
  email: string;
  full_name?: string | null;
  is_active: boolean;
  is_superuser: boolean;
  roles: string[];
}

export interface UserCreate extends UserBase {
  password: string;
}

export interface UserUpdate {
  email?: string | null;
  full_name?: string | null;
  is_active?: boolean | null;
  is_superuser?: boolean | null;
  roles?: string[] | null;
  password?: string | null;
}

export interface UserRead extends UserBase {
  id: number;
  created_at: string;   // ISO datetime
  updated_at: string;   // ISO datetime
  avatar_url?: string | null;
}

// --- Auth ---
export interface LoginRequest {
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
  refresh_token?: string | null;
  user?: UserRead;
}

export interface TokenRefreshRequest {
  refresh_token: string;
}

export interface TokenRefreshResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token: string;
}

// --- Assignee ---
export interface Assignee {
  user_id?: number | null;
  name: string;
  email?: string | null;
  role?: string | null;
  avatar_url?: string | null;
  is_active?: boolean | null;
}

// --- Participant ---
export interface Participant {
  name: string;
  email?: string | null;
  role?: string | null;
  avatar_url?: string | null;
  is_team?: boolean | null;
  is_active?: boolean | null;
  joined_at?: string | null;
}

// --- Attachment ---
export interface Attachment {
  url: string;
  type?: string | null;
  name?: string | null;
  size?: number | null;
  uploaded_by?: string | null;
  uploaded_at?: string | null;
  description?: string | null;
  preview_url?: string | null;
}

// --- Project ---
export interface ProjectBase {
  name: string;
  description?: string | null;
  project_status?: string | null;
  deadline?: string | null;
  priority: number;
  tags: string[];
  linked_repo?: string | null;
  color?: string | null;
  participants: Participant[];
  custom_fields: Record<string, any>;
  parent_project_id?: number | null;
  attachments: Attachment[];
  is_favorite: boolean;
  ai_notes?: string | null;
  external_id?: string | null;
  subscription_level?: string | null;
  author_id?: number | null;
  team_id?: number | null;
}

export interface ProjectCreate extends Omit<ProjectBase, 'author_id'> {}

export interface ProjectUpdate {
  name?: string | null;
  description?: string | null;
  project_status?: string | null;
  deadline?: string | null;
  priority?: number | null;
  tags?: string[] | null;
  linked_repo?: string | null;
  color?: string | null;
  participants?: Participant[] | null;
  custom_fields?: Record<string, any> | null;
  parent_project_id?: number | null;
  attachments?: Attachment[] | null;
  is_favorite?: boolean | null;
  ai_notes?: string | null;
  external_id?: string | null;
  subscription_level?: string | null;
  author_id?: number | null;
  team_id?: number | null;
}

export interface ProjectShort {
  id: number;
  name: string;
  author_id?: number | null;
}

export interface ProjectRead extends ProjectBase {
  id: number;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

// --- Task ---
export interface TaskBase {
  title: string;
  description?: string | null;
  task_status: string;
  priority: number;
  deadline?: string | null;
  assignees: Assignee[];
  tags: string[];
  project_id: number;
  parent_task_id?: number | null;
  custom_fields: Record<string, any>;
  attachments: Attachment[];
  is_favorite: boolean;
  ai_notes?: string | null;
  external_id?: string | null;
  reviewed: boolean;
}

export interface TaskCreate extends TaskBase {}

export interface TaskUpdate {
  title?: string | null;
  description?: string | null;
  task_status?: string | null;
  priority?: number | null;
  deadline?: string | null;
  assignees?: Assignee[] | null;
  tags?: string[] | null;
  project_id?: number | null;
  parent_task_id?: number | null;
  custom_fields?: Record<string, any> | null;
  attachments?: Attachment[] | null;
  is_favorite?: boolean | null;
  ai_notes?: string | null;
  external_id?: string | null;
  reviewed?: boolean | null;
}

export interface TaskShort {
  id: number;
  title: string;
  project_id: number;
  task_status: string;
}

export interface TaskRead extends TaskBase {
  id: number;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
  task_status: string;
}

// --- DevLog ---
export interface DevLogBase {
  project_id?: number | null;
  task_id?: number | null;
  entry_type: string;
  content: string;
  author_id?: number | null;
  tags: string[];
  custom_fields: Record<string, any>;
  attachments: Attachment[];
  edit_reason?: string | null;
  ai_notes?: string | null;
}

export interface DevLogCreate extends Omit<DevLogBase, 'author_id'> {}

export interface DevLogUpdate {
  project_id?: number | null;
  task_id?: number | null;
  entry_type?: string | null;
  content?: string | null;
  tags?: string[] | null;
  custom_fields?: Record<string, any> | null;
  attachments?: Attachment[] | null;
  edit_reason?: string | null;
  ai_notes?: string | null;
}

export interface DevLogShort {
  id: number;
  entry_type: string;
  content: string;
  author_id: number;
  created_at?: string | null;
  author?: UserRead | null;
}

export interface DevLogRead extends DevLogBase {
  id: number;
  author_id: number;
  created_at: string;
  updated_at?: string | null;
  is_deleted: boolean;
  author?: UserRead | null;
}

// --- Plugin ---
export interface PluginBase {
  name: string;
  description?: string | null;
  config_json: Record<string, any>;
  is_active?: boolean | null;
  version?: string | null;
  author?: string | null;
  subscription_level?: string | null;
  is_private?: boolean | null;
  ui_component?: string | null;
  tags: string[];
  is_deleted: boolean;
  deleted_at?: string | null;
}

export interface PluginCreate extends Omit<PluginBase, 'is_deleted' | 'deleted_at'> {}

export interface PluginUpdate {
  name?: string | null;
  description?: string | null;
  config_json?: Record<string, any> | null;
  is_active?: boolean | null;
  version?: string | null;
  author?: string | null;
  subscription_level?: string | null;
  is_private?: boolean | null;
  ui_component?: string | null;
  tags?: string[] | null;
}

export interface PluginShort {
  id: number;
  name: string;
  is_active: boolean;
  is_deleted: boolean;
}

export interface PluginRead extends PluginBase {
  id: number;
}

// --- Settings ---
export interface SettingBase {
  key: string;
  value: any;
  description?: string | null;
  is_active?: boolean | null;
}

export interface SettingCreate extends SettingBase {
  user_id?: number | null;
}

export interface SettingUpdate {
  value?: any;
  description?: string | null;
  is_active?: boolean | null;
}

export interface SettingRead extends SettingBase {
  id: number;
  user_id?: number | null;
  created_at: string;
  updated_at: string;
}

// --- Template ---
export interface TemplateBase {
  name: string;
  description?: string | null;
  version?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  is_active?: boolean | null;
  tags: string[];
  structure: Record<string, any>;
  ai_notes?: string | null;
  subscription_level?: string | null;
  is_private?: boolean | null;
  is_deleted: boolean;
  deleted_at?: string | null;
}

export interface TemplateCreate {
  name: string;
  description?: string | null;
  version?: string | null;
  is_active?: boolean | null;
  tags?: string[];
  structure: Record<string, any>;
  ai_notes?: string | null;
  subscription_level?: string | null;
  is_private?: boolean | null;
}

export interface TemplateUpdate {
  name?: string | null;
  description?: string | null;
  version?: string | null;
  is_active?: boolean | null;
  tags?: string[] | null;
  structure?: Record<string, any> | null;
  ai_notes?: string | null;
  subscription_level?: string | null;
  is_private?: boolean | null;
}

export interface TemplateShort {
  id: number;
  name: string;
  is_active: boolean;
  is_private: boolean;
  author_id: number;
  author?: UserRead | null;
  is_deleted: boolean;
}
export interface cloneTemplate {
  id: number;
  name: string;
  is_active: boolean;
  is_private: boolean;
  author_id: number;
  author?: UserRead | null;
  is_deleted: boolean;
}
export interface TemplateRead extends TemplateBase {
  id: number;
  author_id: number;
  author?: UserRead | null;
}

// --- Team ---
export interface TeamBase {
  name: string;
  description?: string | null;
}

export interface TeamCreate extends TeamBase {}

export interface TeamUpdate {
  name?: string | null;
  description?: string | null;
}

export interface TeamRead extends TeamBase {
  id: number;
  owner_id?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
  is_deleted?: boolean | null;
}

// --- AI Context ---
export interface AIContextBase {
  object_type: string;
  object_id: number;
  context_data: Record<string, any>;
  created_by?: string | null;
  request_id?: string | null;
  notes?: string | null;
}

export interface AIContextCreate extends AIContextBase {}

export interface AIContextUpdate {
  object_type?: string | null;
  object_id?: number | null;
  context_data?: Record<string, any> | null;
  created_by?: string | null;
  request_id?: string | null;
  notes?: string | null;
  is_deleted?: boolean | null;
}

export interface AIContextRead extends AIContextBase {
  id: number;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

// --- Jarvis Chat ---
export interface ChatMessageBase {
  project_id: number;
  role: string;
  content: string;
  timestamp?: string | null;
  metadata?: Record<string, any> | null;
  author?: string | null;
  ai_notes?: string | null;
  attachments: Attachment[];
  is_deleted: boolean;
}

export interface ChatMessageCreate extends ChatMessageBase {}

export interface ChatMessageUpdate {
  content?: string | null;
  metadata?: Record<string, any> | null;
  author?: string | null;
  ai_notes?: string | null;
  attachments?: Attachment[] | null;
  is_deleted?: boolean | null;
}

export interface ChatMessageRead extends ChatMessageBase {
  id: number;
}

export interface ChatMessageShort {
  id: number;
  role: string;
  content: string;
  timestamp?: string | null;
}

// --- AI Contexts for entities (optional, для AI features) ---
export interface ProjectAIContext {
  id: number;
  name: string;
  description?: string | null;
  status?: string | null;
  deadline?: string | null;
  priority?: number | null;
  participants: Record<string, any>[];
  tags: string[];
  linked_repo?: string | null;
  parent_project_id?: number | null;
  custom_fields: Record<string, any>;
  is_overdue?: boolean | null;
  is_deleted?: boolean | null;
  ai_notes?: string | null;
  external_id?: string | null;
  subscription_level?: string | null;
  attachments: Record<string, any>[];
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TaskAIContext {
  id: number;
  project_id: number;
  parent_task_id?: number | null;
  title: string;
  description?: string | null;
  status?: string | null;
  priority?: number | null;
  deadline?: string | null;
  assignees: Record<string, any>[];
  tags: string[];
  custom_fields: Record<string, any>;
  created_at?: string | null;
  updated_at?: string | null;
  is_overdue?: boolean | null;
  is_deleted?: boolean | null;
  attachments: Record<string, any>[];
  is_favorite?: boolean | null;
  ai_notes?: string | null;
  external_id?: string | null;
  reviewed?: boolean | null;
}

export interface DevLogAIContext {
  id: number;
  project_id?: number | null;
  task_id?: number | null;
  entry_type: string;
  content: string;
  author: string;
  tags: string[];
  created_at?: string | null;
  updated_at?: string | null;
  custom_fields: Record<string, any>;
  is_deleted?: boolean | null;
  edit_reason?: string | null;
  attachments: Record<string, any>[];
  ai_notes?: string | null;
}

export interface UserAIContext {
  id: number;
  username: string;
  email: string;
  full_name?: string | null;
  roles: string[];
  is_superuser?: boolean | null;
  is_active?: boolean | null;
  created_at?: string | null;
  avatar_url?: string | null;
}

export interface PluginAIContext {
  id: number;
  name: string;
  description?: string | null;
  config_json: Record<string, any>;
  is_active?: boolean | null;
  version?: string | null;
  author?: string | null;
  subscription_level?: string | null;
  is_private?: boolean | null;
  ui_component?: string | null;
  tags: string[];
}
// --- FILTERS для list-запросов ---
// Task list /tasks/?task_status=...&assignee_id=...&project_id=...&is_deleted=...
export interface TaskFilters {
  task_status?: string;             // например: "todo", "in_progress"
  assignee_id?: number | number[];  // поддержка одиночного или нескольких исполнителей
  project_id?: number;              // задачи по проекту
  is_deleted?: boolean;             // только удалённые (архив)
  is_favorite?: boolean;
  reviewed?: boolean;
  title__icontains?: string;        // поиск по части названия
  // ... любые другие query параметры, поддерживаемые бекендом
  [key: string]: any;               // fallback для совместимости (лучше указать явно!)
}

// Project list /projects/?is_deleted=...
export interface ProjectFilters {
  author_id?: number;
  is_deleted?: boolean;
  is_favorite?: boolean;
  name__icontains?: string;         // поиск по части имени
  tags?: string | string[];
  team_id?: number;
  // ...etc
  [key: string]: any;
}

// Template list /templates/?author_id=...&is_deleted=...
export interface TemplateFilters {
  author_id?: number;
  is_deleted?: boolean;
  is_active?: boolean;
  name__icontains?: string;
  tags?: string | string[];
  // ...
  [key: string]: any;
}

// Team list
export interface TeamFilters {
  owner_id?: number;
  is_deleted?: boolean;
  name__icontains?: string;
  // ...
  [key: string]: any;
}

// Plugin list
export interface PluginFilters {
  is_active?: boolean;
  is_deleted?: boolean;
  name__icontains?: string;
  // ...
  [key: string]: any;
}
