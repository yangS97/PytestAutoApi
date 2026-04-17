/**
 * 这里集中放“平台骨架阶段”的共享类型。
 * 新手如果想快速理解页面之间如何衔接，可以优先看本文件：
 * 1. 哪些页面会出现在左侧导航
 * 2. 每个页面目前依赖什么占位数据
 * 3. 后续真实 API 需要返回哪些最小字段
 */

export type RouteName =
  | 'dashboard'
  | 'cases'
  | 'suites'
  | 'environments'
  | 'runs'
  | 'schedules';

export interface NavigationItem {
  name: RouteName;
  label: string;
  shortLabel: string;
  description: string;
}

export interface DashboardMetric {
  key: string;
  label: string;
  value: string;
  description: string;
  trend: string;
}

export type StatusTone = 'success' | 'warning' | 'running' | 'neutral' | 'attention';

export type ApiDataSource = 'api' | 'compatibility' | 'mock';

export interface ApiResolvedData<T> {
  data: T;
  source: ApiDataSource;
  note?: string;
}

export interface FocusItem {
  id: string;
  title: string;
  owner: string;
  status: 'stable' | 'attention' | 'planned';
  summary: string;
}

export type RunStatus = 'queued' | 'running' | 'success' | 'failed' | 'warning';

export interface RunSummary {
  id: string;
  name: string;
  target: string;
  status: RunStatus;
  startedAt: string;
  duration: string;
  starter: string;
  rawStatus?: string;
  note?: string;
  errorSummary?: string;
}

export interface DashboardOverview {
  metrics: DashboardMetric[];
  focusItems: FocusItem[];
  recentRuns: RunSummary[];
}

export interface CaseSummary {
  id: string;
  name: string;
  module: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  priority: 'P0' | 'P1' | 'P2';
  status: 'draft' | 'active';
}

export interface SuiteSummary {
  id: string;
  name: string;
  caseCount: number;
  lastRun: string;
  schedule: string;
}

export interface EnvironmentSummary {
  id: string;
  name: string;
  baseUrl: string;
  authMode: string;
  status: 'online' | 'draft';
}

export interface ScheduleSummary {
  id: string;
  name: string;
  cron: string;
  target: string;
  lastRun: string;
  status: 'active' | 'paused';
}
