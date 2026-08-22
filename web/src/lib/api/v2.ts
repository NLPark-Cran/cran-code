/* Cran Code API v2 client (hand-written until OpenAPI spec is generated) */

const API_BASE = "/api/v2";

function handleAuthError(): never {
  // Mirror clearAuthToken to evict all known auth keys, then force login.
  localStorage.removeItem("cran_auth_token");
  localStorage.removeItem("cran_auth_token_ts");
  localStorage.removeItem("cran_v2_auth_token");
  localStorage.removeItem("cran-auth-store");
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
  throw new Error("Invalid authentication credentials");
}

async function _fetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem("cran_v2_auth_token");
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
    if (res.status === 401) {
      handleAuthError();
    }
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export interface RegisterReq {
  email: string;
  username: string;
  password: string;
  display_name?: string;
}

export interface LoginReq {
  email: string;
  password: string;
}

export interface UserProfile {
  id: string;
  email: string;
  username: string;
  display_name: string | null;
  avatar_url: string | null;
  role: string;
  created_at: string;
}

export interface TokenRes {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface TeamRes {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  /** IANA timezone used to bucket the team's usage by local date (null = UTC). */
  timezone: string | null;
  owner_id: string;
  members: TeamMemberRes[];
  created_at: string;
}

export interface TeamMemberRes {
  id: string;
  user_id: string;
  username: string;
  display_name: string | null;
  role: string;
  joined_at: string;
}

export interface TeamCreateReq {
  name: string;
  slug: string;
  description?: string;
}

export interface TeamUpdateReq {
  name?: string;
  slug?: string;
  description?: string;
  /** IANA timezone (e.g. "Asia/Shanghai"); empty string clears back to UTC. */
  timezone?: string;
}

export interface ProjectRes {
  id: string;
  team_id: string;
  name: string;
  slug: string;
  description: string | null;
  work_dir: string | null;
  git_repo_url: string | null;
  default_model: string | null;
  created_by: string | null;
  members: ProjectMemberRes[];
  created_at: string;
}

export interface ProjectMemberRes {
  id: string;
  user_id: string;
  username: string;
  display_name: string | null;
  role: string;
  joined_at: string;
}

export interface ProjectCreateReq {
  team_id: string;
  name: string;
  slug: string;
  description?: string;
  work_dir?: string;
  git_repo_url?: string;
  default_model?: string;
}

export interface ActivityRes {
  id: string;
  project_id: string;
  user_id: string | null;
  username: string | null;
  display_name: string | null;
  type: string;
  payload: string | null;
  created_at: string;
}

export interface ActivityCreateReq {
  type: string;
  payload?: string;
}

export interface FsEntry {
  name: string;
  path: string;
  type: string;
  size?: number;
}

export interface ProviderModelSpec {
  model: string;
  max_context_size: number;
  capabilities: string[] | null;
  display_name: string | null;
}

export interface ProviderInfo {
  key: string;
  type: string;
  base_url: string;
  has_api_key: boolean;
  models: ProviderModelSpec[];
  /** Config model keys, same order as `models` (used for select). */
  model_keys: string[];
}

export interface ProviderListRes {
  default_model: string;
  default_thinking: boolean;
  providers: ProviderInfo[];
}

export interface ProviderUpsertReq {
  key: string;
  type: string;
  base_url: string;
  /** Omit on update to keep the stored key. */
  api_key?: string | null;
  /** Omit on create to auto-fetch from `{base_url}/models`. */
  models?: ProviderModelSpec[] | null;
  custom_headers?: Record<string, string> | null;
  reasoning_key?: string | null;
}

export interface FetchModelsReq {
  base_url: string;
  type?: string;
  api_key?: string;
  /** Reuse the stored key of this provider when `api_key` is omitted. */
  provider_key?: string;
}

export interface SelectModelReq {
  default_model: string;
  default_thinking?: boolean;
  restart_running_sessions?: boolean;
  force_restart_busy_sessions?: boolean;
}

export interface SelectModelRes {
  default_model: string;
  default_thinking: boolean;
  restarted_session_ids: string[] | null;
  skipped_busy_session_ids: string[] | null;
}

export interface ModelContextReq {
  max_context_size: number;
  restart_running_sessions?: boolean;
}

export interface ProviderKeyRes {
  provider_key: string;
  has_api_key: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface UsageSummaryRes {
  provider_key: string;
  source: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  quota_tokens: number | null;
  remaining_tokens: number | null;
}

export interface UsageDailyPointRes {
  date: string;
  provider_key: string;
  model: string;
  source: string;
  input_tokens: number;
  output_tokens: number;
}

export interface AdminUsageDailyPointRes extends UsageDailyPointRes {
  user_id: string;
  username: string;
}

export const v2Api = {
  auth: {
    register: (data: RegisterReq) =>
      _fetch<TokenRes>("/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    login: (data: LoginReq) =>
      _fetch<TokenRes>("/auth/login", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
  users: {
    me: () => _fetch<UserProfile>("/users/me"),
    updateMe: (data: { display_name?: string; avatar_url?: string }) =>
      _fetch<UserProfile>("/users/me", {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    search: (q: string) =>
      _fetch<UserProfile[]>(`/users/search?q=${encodeURIComponent(q)}`),
    setRole: (userId: string, role: string) =>
      _fetch<UserProfile>(`/users/${encodeURIComponent(userId)}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      }),
    meProviderKeys: () => _fetch<ProviderKeyRes[]>("/users/me/provider-keys"),
    putMeProviderKey: (providerKey: string, apiKey: string) =>
      _fetch<ProviderKeyRes>(
        `/users/me/provider-keys/${encodeURIComponent(providerKey)}`,
        { method: "PUT", body: JSON.stringify({ api_key: apiKey }) },
      ),
    deleteMeProviderKey: (providerKey: string) =>
      _fetch<{ detail: string }>(
        `/users/me/provider-keys/${encodeURIComponent(providerKey)}`,
        { method: "DELETE" },
      ),
    meUsage: () => _fetch<UsageSummaryRes[]>("/users/me/usage"),
    meUsageDaily: (days = 30, tz?: string) =>
      _fetch<UsageDailyPointRes[]>(
        `/users/me/usage/daily?days=${days}${tz ? `&tz=${encodeURIComponent(tz)}` : ""}`,
      ),
  },
  admin: {
    usage: (days = 30, tz?: string) =>
      _fetch<AdminUsageDailyPointRes[]>(
        `/admin/usage?days=${days}${tz ? `&tz=${encodeURIComponent(tz)}` : ""}`,
      ),
  },
  teams: {
    list: () => _fetch<TeamRes[]>("/teams"),
    create: (data: TeamCreateReq) =>
      _fetch<TeamRes>("/teams", { method: "POST", body: JSON.stringify(data) }),
    get: (id: string) => _fetch<TeamRes>(`/teams/${id}`),
    update: (id: string, data: TeamUpdateReq) =>
      _fetch<TeamRes>(`/teams/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    addMember: (teamId: string, userId: string, role?: string) =>
      _fetch<TeamRes>(`/teams/${teamId}/members?user_id=${userId}${role ? `&role=${role}` : ""}`, {
        method: "POST",
      }),
    updateMember: (teamId: string, memberId: string, role: string) =>
      _fetch<TeamRes>(`/teams/${teamId}/members/${memberId}`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      }),
    removeMember: (teamId: string, memberId: string) =>
      _fetch<{ detail: string }>(`/teams/${teamId}/members/${memberId}`, {
        method: "DELETE",
      }),
    listProviderKeys: (teamId: string) =>
      _fetch<ProviderKeyRes[]>(`/teams/${teamId}/provider-keys`),
    putProviderKey: (teamId: string, providerKey: string, apiKey: string) =>
      _fetch<ProviderKeyRes>(
        `/teams/${teamId}/provider-keys/${encodeURIComponent(providerKey)}`,
        { method: "PUT", body: JSON.stringify({ api_key: apiKey }) },
      ),
    deleteProviderKey: (teamId: string, providerKey: string) =>
      _fetch<{ detail: string }>(
        `/teams/${teamId}/provider-keys/${encodeURIComponent(providerKey)}`,
        { method: "DELETE" },
      ),
  },
  projects: {
    list: (teamId?: string) =>
      _fetch<ProjectRes[]>(`/projects${teamId ? `?team_id=${teamId}` : ""}`),
    create: (data: ProjectCreateReq) =>
      _fetch<ProjectRes>("/projects", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    get: (id: string) => _fetch<ProjectRes>(`/projects/${id}`),
    update: (id: string, data: Partial<ProjectCreateReq>) =>
      _fetch<ProjectRes>(`/projects/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    addMember: (projectId: string, userId: string, role?: string) =>
      _fetch<ProjectRes>(`/projects/${projectId}/members?user_id=${userId}${role ? `&role=${role}` : ""}`, {
        method: "POST",
      }),
    updateMember: (projectId: string, memberId: string, role: string) =>
      _fetch<ProjectRes>(`/projects/${projectId}/members/${memberId}`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      }),
    removeMember: (projectId: string, memberId: string) =>
      _fetch<{ detail: string }>(`/projects/${projectId}/members/${memberId}`, {
        method: "DELETE",
      }),
    listActivities: (projectId: string, limit?: number) =>
      _fetch<ActivityRes[]>(`/projects/${projectId}/activities${limit ? `?limit=${limit}` : ""}`),
    createActivity: (projectId: string, data: ActivityCreateReq) =>
      _fetch<ActivityRes>(`/projects/${projectId}/activities`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
  git: {
    status: (projectId: string) =>
      _fetch<{ branch: string; ahead: number; behind: number; modified: string[]; staged: string[]; untracked: string[]; clean: boolean }>(
        `/projects/${projectId}/git/status`
      ),
    branches: (projectId: string) =>
      _fetch<Array<{ name: string; current: boolean }>>(`/projects/${projectId}/git/branches`),
    log: (projectId: string, limit?: number) =>
      _fetch<Array<{ hash: string; short_hash: string; message: string; author: string; date: string }>>(
        `/projects/${projectId}/git/log${limit ? `?limit=${limit}` : ""}`
      ),
    diff: (projectId: string, staged?: boolean, path?: string) =>
      _fetch<Array<{ path: string; diff: string }>>(
        `/projects/${projectId}/git/diff?staged=${staged || false}${path ? `&path=${encodeURIComponent(path)}` : ""}`
      ),
    commit: (projectId: string, message: string) =>
      _fetch<{ detail: string; output: string }>(`/projects/${projectId}/git/commit`, {
        method: "POST",
        body: JSON.stringify({ message }),
      }),
  },
  providers: {
    list: () => _fetch<ProviderListRes>("/providers/"),
    create: (data: ProviderUpsertReq) =>
      _fetch<ProviderListRes>("/providers/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (key: string, data: ProviderUpsertReq) =>
      _fetch<ProviderListRes>(`/providers/${encodeURIComponent(key)}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (key: string) =>
      _fetch<ProviderListRes>(`/providers/${encodeURIComponent(key)}`, {
        method: "DELETE",
      }),
    fetchModels: (data: FetchModelsReq) =>
      _fetch<{ models: ProviderModelSpec[] }>("/providers/fetch-models", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    select: (data: SelectModelReq) =>
      _fetch<SelectModelRes>("/providers/select", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    setModelContext: (modelKey: string, data: ModelContextReq) =>
      _fetch<ProviderListRes>(
        `/providers/models/${encodeURIComponent(modelKey)}/context`,
        { method: "POST", body: JSON.stringify(data) },
      ),
  },
  fs: {
    list: (projectId: string, path?: string) =>
      _fetch<{ entries: FsEntry[] }>(
        `/projects/${projectId}/fs?path=${encodeURIComponent(path || "")}`
      ),
    read: (projectId: string, path: string) =>
      _fetch<{ content: string; path: string }>(
        `/projects/${projectId}/fs?path=${encodeURIComponent(path)}`
      ),
    write: (projectId: string, path: string, content: string) =>
      _fetch<{ detail: string; path: string }>(`/projects/${projectId}/fs`, {
        method: "POST",
        body: JSON.stringify({ path, content }),
      }),
    upload: async (projectId: string, file: File, targetDir: string = "") => {
      const formData = new FormData();
      formData.append("file", file);
      const token = localStorage.getItem("cran_v2_auth_token");
      const res = await fetch(
        `${API_BASE}/projects/${projectId}/fs/upload?path=${encodeURIComponent(targetDir)}`,
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        }
      );
      if (!res.ok) {
        if (res.status === 401) {
          handleAuthError();
        }
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      return res.json() as Promise<{ detail: string; path: string }>;
    },
    download: async (projectId: string, path: string, filename?: string) => {
      const token = localStorage.getItem("cran_v2_auth_token");
      const res = await fetch(
        `${API_BASE}/projects/${projectId}/fs/download?path=${encodeURIComponent(path)}`,
        {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }
      );
      if (!res.ok) {
        if (res.status === 401) {
          handleAuthError();
        }
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || path.split("/").pop() || "download";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    },
    delete: (projectId: string, path: string) =>
      _fetch<{ detail: string; path: string }>(
        `/projects/${projectId}/fs?path=${encodeURIComponent(path)}`,
        { method: "DELETE" }
      ),
    copy: (projectId: string, src: string, dst: string) =>
      _fetch<{ detail: string; src: string; dst: string }>(
        `/projects/${projectId}/fs/copy?src=${encodeURIComponent(src)}&dst=${encodeURIComponent(dst)}`,
        { method: "POST" }
      ),
    move: (projectId: string, src: string, dst: string) =>
      _fetch<{ detail: string; src: string; dst: string }>(
        `/projects/${projectId}/fs/move?src=${encodeURIComponent(src)}&dst=${encodeURIComponent(dst)}`,
        { method: "POST" }
      ),
    compress: (projectId: string, path: string, archive: string) =>
      _fetch<{ detail: string; path: string }>(
        `/projects/${projectId}/fs/compress?path=${encodeURIComponent(path)}&archive=${encodeURIComponent(archive)}`,
        { method: "POST" }
      ),
    extract: (projectId: string, archive: string, dest?: string) =>
      _fetch<{ detail: string; path: string }>(
        `/projects/${projectId}/fs/extract?archive=${encodeURIComponent(archive)}${dest ? `&dest=${encodeURIComponent(dest)}` : ""}`,
        { method: "POST" }
      ),
  },
};
