import { normalizeRunDetail } from '@/api/adapters/runs';
import { apiClient } from '@/api/client';
import type { RunDetail } from '@/types/platform';
import { resolveSuiteRunPreset } from '@/utils/suiteRunPresets';

type UnknownRecord = Record<string, unknown>;

const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const readString = (value: unknown) => (typeof value === 'string' ? value : '');

const readRunId = (payload: unknown) => {
  if (!isRecord(payload)) {
    return '';
  }

  return readString(payload.run_id) || readString(payload.runId) || readString(payload.id);
};

export const executionApi = {
  getRunDetail,
  executeRunNow,
  runSuiteNow,
};

async function getRunDetail(runId: string): Promise<RunDetail> {
  const payload = await apiClient.get<unknown>(`/runs/${runId}`);
  return normalizeRunDetail(payload, 0);
}

async function executeRunNow(runId: string): Promise<RunDetail> {
  const payload = await apiClient.post<unknown>(`/worker/runs/${runId}/execute`);
  return normalizeRunDetail(payload, 0);
}

async function runSuiteNow(suiteId: string): Promise<RunDetail> {
  const preset = resolveSuiteRunPreset(suiteId);
  if (!preset) {
    throw new Error(`当前套件暂未配置一键运行预设：${suiteId}`);
  }

  // 先创建 run，再立即按 run_id 定向执行，保证“点哪个跑哪个”。
  const createdPayload = await apiClient.post<unknown>(`/demo-suites/${suiteId}/runs`, {
    mode: preset.mode,
    environment_id: preset.environmentId,
    requested_by: preset.requestedBy,
  });
  const runId = readRunId(createdPayload);

  if (!runId) {
    throw new Error('后端未返回有效的 run_id，无法继续立即执行。');
  }

  return executeRunNow(runId);
}
