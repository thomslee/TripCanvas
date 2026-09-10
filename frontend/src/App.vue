<script setup lang="ts">
</script>

<template>
  <div class="app-shell">
    <van-nav-bar title="途迹 TripCanvas" fixed placeholder>
      <template #right>
        <span class="nav-ver">v0.1</span>
      </template>
    </van-nav-bar>
    <router-view />
  </div>
</template>

<style scoped>
.nav-ver {
  font-size: 12px;
  color: var(--tc-ink-3);
}
</style>
