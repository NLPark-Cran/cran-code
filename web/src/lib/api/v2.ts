/* Cran Code API v2 client (hand-written until OpenAPI spec is generated) */

const API_BASE = "/api/v2";

async function _fetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem("cran_auth_token");
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
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
  },
  teams: {
    list: () => _fetch<TeamRes[]>("/teams"),
    create: (data: TeamCreateReq) =>
      _fetch<TeamRes>("/teams", { method: "POST", body: JSON.stringify(data) }),
    get: (id: string) => _fetch<TeamRes>(`/teams/${id}`),
    update: (id: string, data: Partial<TeamCreateReq>) =>
      _fetch<TeamRes>(`/teams/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
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
  },
};
