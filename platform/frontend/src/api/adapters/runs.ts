import type { RunSummary } from '@/types/platform';
import { normalizeRunStatus } from '@/utils/runStatus';

type UnknownRecord = Record<string, unknown>;

const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const readString = (value: unknown) => (typeof value === 'string' ? value : '');
const readFirstString = (...values: unknown[]) => values.map(readString).find(Boolean) ?? '';

const formatDateTime = (rawValue: unknown) => {
  const text = readString(rawValue);

  if (!text) {
    return '未记录';
  }

  const parsedDate = new Date(text);

  if (Number.isNaN(parsedDate.getTime())) {
    return text;
  }

  return parsedDate.toLocaleString('zh-CN', { hour12: false });
};

const formatDuration = (rawValue: unknown, rawStatus?: string) => {
  if (typeof rawValue === 'number' && Number.isFinite(rawValue)) {
    if (rawValue >= 1000) {
      const totalSeconds = Math.round(rawValue / 1000);
      const minutes = Math.floor(totalSeconds / 60);
      const seconds = totalSeconds % 60;
      return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
    }

    return `${rawValue}ms`;
  }

  if (typeof rawValue === 'string' && rawValue.trim()) {
    return rawValue;
  }

  const normalizedStatus = normalizeRunStatus(rawStatus);

  if (normalizedStatus === 'queued') {
    return '等待调度';
  }

  if (normalizedStatus === 'running') {
    return '执行中';
  }

  return '-';
};

/**
 * 后端列表接口在迭代期很容易出现多种壳结构：
 * - 直接返回数组
 * - { items: [...] }
 * - { data: [...] }
 * - { runs: [...] }
 *
 * RunsPage 和 Dashboard 兼容层都共用这段抽取逻辑，避免两边各自猜字段。
 */
export const extractRunCollection = (payload: unknown): unknown[] => {
  if (Array.isArray(payload)) {
    return payload;
  }

  if (!isRecord(payload)) {
    return [];
  }

  const candidates = ['items', 'data', 'results', 'runs', 'records', 'list'] as const;

  for (const key of candidates) {
    const value = payload[key];

    if (Array.isArray(value)) {
      return value;
    }
  }

  return [];
};

export const normalizeRunSummary = (payload: unknown, index: number): RunSummary => {
  if (!isRecord(payload)) {
    return {
      id: `run-${index}`,
      name: '未命名运行',
      target: '未知目标',
      status: 'warning',
      startedAt: '未记录',
      duration: '-',
      starter: '未知来源',
    };
  }

  const rawStatus = readFirstString(payload.status, payload.run_status, payload.state, payload.result);
  const target = readFirstString(payload.target, payload.suite_id, payload.case_id);

  return {
    id: readFirstString(payload.id, payload.run_id) || `run-${index}`,
    name: readFirstString(payload.name, payload.title) || target || `运行 ${index + 1}`,
    target: target || '未标记目标',
    status: normalizeRunStatus(rawStatus),
    startedAt: formatDateTime(payload.started_at ?? payload.startedAt ?? payload.created_at ?? payload.createdAt),
    duration: formatDuration(payload.duration ?? payload.duration_ms ?? payload.elapsed_ms, rawStatus),
    starter: readFirstString(
      payload.starter,
      payload.requested_by,
      payload.requestedBy,
      payload.trigger_source,
      payload.triggerSource,
    ) || '未知来源',
    rawStatus: rawStatus || undefined,
    note: readFirstString(payload.note, payload.remark, payload.message, payload.summary) || undefined,
    errorSummary:
      readFirstString(
        payload.error,
        payload.error_message,
        payload.errorMessage,
        payload.failure_reason,
        payload.failureReason,
      ) || undefined,
  };
};
