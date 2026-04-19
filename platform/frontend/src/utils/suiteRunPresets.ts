import type { SuiteRunPreset } from '@/types/platform';

/**
 * 当前平台先只把“真正能跑通的样例套件”做成一键运行。
 * 这样前端不需要临时拼参数，用户点击后就能直接进入执行闭环。
 */
const suiteRunPresetMap: Record<string, SuiteRunPreset> = {
  'demo-login-auth': {
    suiteId: 'demo-login-auth',
    environmentId: 'env-default-live',
    mode: 'live',
    requestedBy: 'platform-ui',
  },
  'demo-persona-library': {
    suiteId: 'demo-persona-library',
    environmentId: 'env-demo-mock',
    mode: 'mock',
    requestedBy: 'platform-ui',
  },
};

export const resolveSuiteRunPreset = (suiteId: string): SuiteRunPreset | null =>
  suiteRunPresetMap[suiteId] ?? null;
