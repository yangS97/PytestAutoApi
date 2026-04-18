/**
 * API client 的职责只有一个：把页面/Pinia 中散落的 fetch 细节收口。
 *
 * 这样做的好处：
 * 1. 后续接入统一鉴权头、请求追踪、错误提示时，只改这一层。
 * 2. 页面组件只关心“要什么数据”，不关心“怎么拼 URL / 怎么 parse JSON”。
 * 3. 当前骨架使用 mock，未来切到真实 FastAPI 时，页面基本不用重写。
 */

type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  query?: Record<string, QueryValue>;
  body?: BodyInit | Record<string, unknown> | null;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly payload?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// 当前真实后端默认挂在 /api/v1，下游环境如果有代理改写，再通过 VITE_API_BASE_URL 覆盖。
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api/v1').replace(/\/$/, '');

const buildUrl = (path: string, query?: Record<string, QueryValue>) => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = new URL(`${API_BASE_URL}${normalizedPath}`, window.location.origin);

  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
  }

  return url.toString();
};

const parsePayload = async (response: Response) => {
  const text = await response.text();

  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
};

const normalizeBody = (body: RequestOptions['body']) => {
  if (body === null || body === undefined) {
    return undefined;
  }

  if (body instanceof FormData || body instanceof URLSearchParams || typeof body === 'string') {
    return body;
  }

  return JSON.stringify(body);
};

const shouldAttachJsonHeader = (body: RequestOptions['body']) => {
  if (body === null || body === undefined) {
    return false;
  }

  if (body instanceof FormData || body instanceof URLSearchParams || typeof body === 'string') {
    return false;
  }

  return true;
};

export const apiClient = {
  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { query, body, headers, ...rest } = options;
    const response = await fetch(buildUrl(path, query), {
      ...rest,
      headers: {
        Accept: 'application/json',
        ...(shouldAttachJsonHeader(body) ? { 'Content-Type': 'application/json' } : {}),
        ...headers,
      },
      body: normalizeBody(body),
    });

    const payload = await parsePayload(response);

    if (!response.ok) {
      throw new ApiError(`请求 ${path} 失败`, response.status, payload);
    }

    return payload as T;
  },

  get<T>(path: string, query?: Record<string, QueryValue>) {
    return this.request<T>(path, { method: 'GET', query });
  },

  post<T>(path: string, body?: RequestOptions['body']) {
    return this.request<T>(path, { method: 'POST', body });
  },

  patch<T>(path: string, body?: RequestOptions['body']) {
    return this.request<T>(path, { method: 'PATCH', body });
  },

  delete<T>(path: string) {
    return this.request<T>(path, { method: 'DELETE' });
  },
};

export const isApiError = (error: unknown): error is ApiError => error instanceof ApiError;
