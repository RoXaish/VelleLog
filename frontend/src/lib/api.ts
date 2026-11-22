export interface User {
  id: number;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface Credentials {
  email: string;
  password: string;
}

export type Mood =
  | 'happy'
  | 'calm'
  | 'excited'
  | 'grateful'
  | 'neutral'
  | 'sad'
  | 'anxious'
  | 'stressed';

export interface TagSummary {
  id: number;
  name: string;
}

export interface Tag {
  id: number;
  user_id: number;
  name: string;
  entry_count: number;
  created_at: string;
  updated_at: string;
}

export interface JournalEntry {
  id: number;
  user_id: number;
  title: string;
  content: string;
  mood: Mood | null;
  tags: TagSummary[];
  created_at: string;
  updated_at: string;
}

export interface JournalEntryInput {
  title: string;
  content: string;
  mood?: Mood | null;
  tag_ids?: number[];
}

export interface JournalEntryList {
  items: JournalEntry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface JournalEntryListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  tagIds?: number[];
  mood?: Mood | null;
}

export interface Dashboard {
  total_entries: number;
  entries_this_week: number;
  current_streak: number;
  recent_entries: JournalEntry[];
}

interface LoginResponse {
  access_token: string;
  token_type: string;
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '');
const CSRF_COOKIE_NAME = 'velle_csrf_token';
const CSRF_HEADER_NAME = 'X-CSRF-Token';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function readCookie(name: string): string | null {
  for (const part of document.cookie.split(';')) {
    const trimmed = part.trim();
    const separator = trimmed.indexOf('=');
    if (separator === -1 || trimmed.slice(0, separator) !== name) continue;

    try {
      return decodeURIComponent(trimmed.slice(separator + 1));
    } catch {
      return null;
    }
  }
  return null;
}

function errorMessage(body: unknown): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) =>
          item && typeof item === 'object' && 'msg' in item
            ? String((item as { msg: unknown }).msg)
            : null
        )
        .filter((message): message is string => Boolean(message));
      if (messages.length > 0) return messages.join(' ');
    }
  }
  return 'Something went wrong. Please try again.';
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase();
  const headers = new Headers(init.headers);

  if (init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (method !== 'GET' && method !== 'HEAD') {
    const csrfToken = readCookie(CSRF_COOKIE_NAME);
    if (csrfToken) {
      headers.set(CSRF_HEADER_NAME, csrfToken);
    }
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      method,
      headers,
      credentials: 'include',
    });
  } catch {
    throw new ApiError(
      0,
      'Unable to reach the server. Check your connection and try again.'
    );
  }

  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      body = null;
    }
    throw new ApiError(response.status, errorMessage(body));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const authApi = {
  register(payload: Credentials): Promise<User> {
    return request<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async login(payload: Credentials): Promise<void> {
    await request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  me(): Promise<User> {
    return request<User>('/auth/me');
  },

  async logout(): Promise<void> {
    await request<void>('/auth/logout', { method: 'POST' });
  },
};

export const journalApi = {
  list({
    page = 1,
    pageSize = 10,
    search = '',
    tagIds = [],
    mood = null,
  }: JournalEntryListParams = {}): Promise<JournalEntryList> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (search.trim()) params.set('search', search.trim());
    tagIds.forEach((tagId) => params.append('tag_ids', String(tagId)));
    if (mood) params.set('mood', mood);

    return request<JournalEntryList>(`/journal-entries?${params.toString()}`);
  },

  get(entryId: number | string): Promise<JournalEntry> {
    return request<JournalEntry>(`/journal-entries/${entryId}`);
  },

  create(payload: JournalEntryInput): Promise<JournalEntry> {
    return request<JournalEntry>('/journal-entries', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  update(
    entryId: number | string,
    payload: Partial<JournalEntryInput>
  ): Promise<JournalEntry> {
    return request<JournalEntry>(`/journal-entries/${entryId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  remove(entryId: number | string): Promise<void> {
    return request<void>(`/journal-entries/${entryId}`, { method: 'DELETE' });
  },
};

export const tagsApi = {
  list(): Promise<Tag[]> {
    return request<Tag[]>('/tags');
  },

  create(name: string): Promise<Tag> {
    return request<Tag>('/tags', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  },

  update(tagId: number | string, name: string): Promise<Tag> {
    return request<Tag>(`/tags/${tagId}`, {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    });
  },

  remove(tagId: number | string): Promise<void> {
    return request<void>(`/tags/${tagId}`, { method: 'DELETE' });
  },
};

export const dashboardApi = {
  get(): Promise<Dashboard> {
    return request<Dashboard>('/dashboard');
  },
};
