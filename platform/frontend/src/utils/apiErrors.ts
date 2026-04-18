import { isApiError } from '@/api/client';

/**
 * 平台页逐步从 mock 切到真实接口后，错误提示要尽量稳定：
 * - API 错误优先展示后端 detail
 * - 兜底保留浏览器/运行时错误
 * - 最后再回到页面提供的默认文案
 */
export const resolveApiErrorMessage = (error: unknown, fallback: string): string => {
  if (isApiError(error)) {
    const payload = error.payload as Record<string, unknown> | undefined;
    const detail = typeof payload?.detail === 'string' ? payload.detail : '';
    return detail || `请求失败，状态码 ${error.status}`;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
};
