<template>
  <div class="app-shell">
    <SideNav />

    <div class="app-shell__body">
      <AppHeader />

      <main class="app-shell__main">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue';
import SideNav from '@/components/layout/SideNav.vue';
</script>

<style scoped>
.app-shell {
  display: grid;
  grid-template-columns: 18.5rem minmax(0, 1fr);
  min-height: 100dvh;
}

.app-shell__body {
  position: relative;
  padding: 0 1.5rem 2rem;
}

.app-shell__body::before {
  content: '';
  position: absolute;
  inset: 0 0 auto auto;
  width: min(38vw, 28rem);
  height: min(38vw, 28rem);
  border-radius: 999px;
  background: radial-gradient(circle, rgba(255, 195, 113, 0.3), transparent 70%);
  filter: blur(10px);
  pointer-events: none;
}

.app-shell__main {
  position: relative;
  display: grid;
  gap: 1.25rem;
}

@media (max-width: 960px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .app-shell__body {
    padding: 0 1rem 1.5rem;
  }
}
</style>

