import 'vue-router';

import type { RouteName } from '@/types/platform';

declare module 'vue-router' {
  interface RouteMeta {
    title: string;
    description: string;
    navLabel: string;
    shortLabel: string;
    section: RouteName;
  }
}

