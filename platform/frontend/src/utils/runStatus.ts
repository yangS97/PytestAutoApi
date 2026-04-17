import type { RunStatus, StatusTone } from '@/types/platform';

interface RunStatusPresentation {
  label: string;
  tone: StatusTone;
  summary: string;
  description: string;
  nextSteps: string[];
}

/**
 * 运行状态会同时来自两类来源：
 * 1. 当前页面里的 mock 数据
 * 2. 后端真实接口里的 queued / succeeded / failed 等原始枚举
 *
 * 这里统一做“后端状态 -> 前端展示状态”的映射，避免 Dashboard 和 Runs 两页各写一套。
 */
const runStatusMetaMap: Record<RunStatus, RunStatusPresentation> = {
  queued: {
    label: '排队中',
    tone: 'neutral',
    summary: '任务已经进入队列，但还没真正开始执行。',
    description: '排队态通常代表调度器已受理请求，接下来要确认 worker 是否空闲、队列是否积压。',
    nextSteps: ['先确认调度队列长度是否异常。', '再检查是否有空闲 worker 可以拉起本次运行。'],
  },
  running: {
    label: '运行中',
    tone: 'running',
    summary: '任务正在执行中，排障重点是判断有没有卡在慢步骤或外部依赖。',
    description: '运行中不代表系统健康，仍要结合耗时、步骤日志和依赖服务状态判断是否存在阻塞。',
    nextSteps: ['优先对照当前耗时与历史平均值。', '再确认外部依赖、数据库或鉴权链路是否变慢。'],
  },
  success: {
    label: '成功',
    tone: 'success',
    summary: '任务已经成功结束，当前更适合作为结果核对和追溯入口。',
    description: '成功态说明主流程通过了当前断言，但如果业务仍异常，还需要继续查看日志、响应片段和下游结果。',
    nextSteps: ['若用户仍反馈异常，继续抽查关键日志和响应片段。', '确认成功结果是否对应了正确环境和正确目标。'],
  },
  failed: {
    label: '失败',
    tone: 'attention',
    summary: '任务已经失败，应优先定位失败步骤和最近变更。',
    description: '失败态是最直接的排障入口，通常要先看错误摘要，再沿着目标、触发人和时间回溯上下文。',
    nextSteps: ['先阅读错误摘要，确认是断言失败、依赖失败还是环境问题。', '结合目标和触发时间回看最近代码、配置或环境变更。'],
  },
  warning: {
    label: '告警',
    tone: 'warning',
    summary: '任务没有完全失败，但存在需要人工确认的异常信号。',
    description: '告警态一般意味着主链路通过了，但有部分步骤、断言或数据校验结果不够稳定。',
    nextSteps: ['确认哪些步骤被标记成非阻塞告警。', '评估是否需要把当前告警升级成阻塞失败。'],
  },
};

export const normalizeRunStatus = (rawStatus?: string | null): RunStatus => {
  const normalizedStatus = rawStatus?.trim().toLowerCase();

  switch (normalizedStatus) {
    case 'queued':
    case 'pending':
      return 'queued';
    case 'running':
    case 'in_progress':
      return 'running';
    case 'succeeded':
    case 'success':
    case 'passed':
      return 'success';
    case 'failed':
    case 'error':
      return 'failed';
    case 'warning':
    case 'partial_success':
      return 'warning';
    default:
      return 'warning';
  }
};

export const getRunStatusMeta = (status: RunStatus) => {
  const { label, tone } = runStatusMetaMap[status];
  return { label, tone };
};

/**
 * 页面层不再自己拼接状态说明文案，而是统一从这里拿：
 * - 文案口径一致
 * - 新页面要复用时不必复制 switch 逻辑
 */
export const getRunStatusInsight = (status: RunStatus) => {
  const { summary, description, nextSteps } = runStatusMetaMap[status];
  return { summary, description, nextSteps };
};
