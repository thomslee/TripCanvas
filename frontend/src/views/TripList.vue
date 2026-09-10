<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { useTripsStore } from '../stores/trips'
import { useUserStore } from '../stores/user'
import { tripsApi } from '../api'

const store = useTripsStore()
const userStore = useUserStore()
const router = useRouter()

onMounted(() => {
  store.fetchTrips().catch((e) => showToast(e.message))
})

function onLogout() {
  userStore.logout()
  router.push('/login')
}

function fmtDate(d: string): string {
  return d ? d.slice(0, 10) : ''
}

function fmtTime(t: string | null): string {
  return t ? t.slice(0, 5) : ''
}

async function onRemove(e: Event, id: number) {
  e.stopPropagation()
  try {
    await showConfirmDialog({ title: '删除行程', message: '确定删除该行程吗？此操作不可恢复。' })
    await store.removeTrip(id)
    showToast('已删除')
  } catch {
    /* 取消 */
  }
}

async function onDuplicate(e: Event, id: number) {
  e.stopPropagation()
  try {
    const { data } = await tripsApi.duplicate(id)
    await store.fetchTrips()
    showToast('已复制')
    router.push(`/trips/${data.id}`)
  } catch (err) {
    showToast((err as Error).message)
  }
}

const statusText: Record<string, string> = {
  draft: '草稿',
  planning: '规划中',
  active: '进行中',
  done: '已完成',
}
</script>

<template>
  <div class="tc-page">
    <div v-if="store.loading" style="padding: 40px 0; text-align: center">
      <van-loading color="#0e7c7e" vertical>加载中…</van-loading>
    </div>

    <template v-else-if="store.trips.length">
      <div class="user-bar">
        <div class="user-info">
          <div class="user-avatar">{{ (userStore.user?.nickname || userStore.user?.username || '?').charAt(0).toUpperCase() }}</div>
          <div class="user-meta">
            <span class="user-name">{{ userStore.user?.nickname || userStore.user?.username }}</span>
            <span class="user-role" :class="userStore.user?.role">{{ userStore.user?.role === 'admin' ? '管理员' : '普通用户' }}</span>
          </div>
        </div>
        <div class="user-actions">
          <button v-if="userStore.isAdmin" class="settings-btn" @click="router.push('/settings')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
            设置
          </button>
          <button class="logout-btn" @click="onLogout">退出</button>
        </div>
      </div>
      <div class="list-head">
        <span class="list-title">我的行程</span>
      </div>
      <div
        v-for="t in store.trips"
        :key="t.id"
        class="tc-card trip-card"
        @click="router.push(`/trips/${t.id}`)"
      >
        <div class="trip-top">
          <span class="trip-title">{{ t.title }}</span>
          <span class="trip-status" :class="t.status">{{ statusText[t.status] || t.status }}</span>
        </div>
        <div class="trip-meta">
          <span>{{ t.depart_city }} → {{ t.dest_city }}</span>
          <span>{{ fmtDate(t.depart_date) }} 至 {{ fmtDate(t.return_date) }}</span>
        </div>
        <div class="trip-foot">
          <span>{{ t.total_days }} 天</span>
          <span v-if="t.arrive_time">到达 {{ fmtTime(t.arrive_time) }}</span>
          <span v-if="t.depart_time">起飞 {{ fmtTime(t.depart_time) }}</span>
          <button class="dup-btn" @click="onDuplicate($event, t.id)">复制</button>
          <button class="del-btn" @click="onRemove($event, t.id)">删除</button>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="user-bar">
        <div class="user-info">
          <div class="user-avatar">{{ (userStore.user?.nickname || userStore.user?.username || '?').charAt(0).toUpperCase() }}</div>
          <div class="user-meta">
            <span class="user-name">{{ userStore.user?.nickname || userStore.user?.username }}</span>
            <span class="user-role" :class="userStore.user?.role">{{ userStore.user?.role === 'admin' ? '管理员' : '普通用户' }}</span>
          </div>
        </div>
        <div class="user-actions">
          <button v-if="userStore.isAdmin" class="settings-btn" @click="router.push('/settings')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
            设置
          </button>
          <button class="logout-btn" @click="onLogout">退出</button>
        </div>
      </div>
      <div class="tc-empty">
      <svg width="52" height="52" viewBox="0 0 24 24" fill="none">
        <path d="M12 21s-7-5.2-7-11a7 7 0 1 1 14 0c0 5.8-7 11-7 11Z" stroke="#7a8e93" stroke-width="1.6" stroke-linejoin="round"/>
        <path d="M9 10.5l2 2 4-4" stroke="#7a8e93" stroke-width="1.6" stroke-linejoin="round"/>
      </svg>
      <div>还没有行程</div>
      <div style="font-size: 12px; margin-top: 4px">输入往返航班，开始第一段旅程</div>
    </div>
    </template>

    <div class="fab">
      <van-button type="primary" round block icon="plus" @click="router.push('/create')">
        新建行程
      </van-button>
    </div>
  </div>
</template>

<style scoped>
.trip-card {
  cursor: pointer;
}
.user-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 4px 14px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, #0e7c7e, #12a5a8);
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.user-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.user-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--tc-ink);
}
.user-role {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  width: fit-content;
}
.user-role.admin {
  background: #fff3e0;
  color: #e65100;
}
.user-role.user {
  background: #e8f5e9;
  color: #2e7d32;
}
.user-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.logout-btn {
  border: 1px solid #d8e0de;
  background: #fff;
  color: #7a8a87;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: 8px;
  padding: 4px 12px;
  cursor: pointer;
}
.list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 2px 10px;
}
.list-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--tc-ink);
}
.settings-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--tc-teal);
  background: #fff;
  color: var(--tc-teal-deep);
  font-size: 12.5px;
  font-weight: 600;
  border-radius: 8px;
  padding: 4px 12px;
  cursor: pointer;
}
.trip-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.trip-title {
  font-size: 16px;
  font-weight: 700;
}
.trip-status {
  font-size: 11px;
  padding: 2px 9px;
  border-radius: 999px;
  background: var(--tc-teal-soft);
  color: var(--tc-teal-deep);
}
.trip-meta {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-top: 9px;
  font-size: 12.5px;
  color: var(--tc-ink-2);
}
.trip-foot {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
  font-size: 12px;
  color: var(--tc-ink-3);
}
.del-btn {
  border: 1px solid var(--tc-line);
  background: #fff;
  color: #c94f4a;
  font-size: 12px;
  border-radius: 8px;
  padding: 3px 12px;
  cursor: pointer;
}
.dup-btn {
  margin-left: auto;
  border: 1px solid var(--tc-teal);
  background: #fff;
  color: var(--tc-teal-deep);
  font-size: 12px;
  border-radius: 8px;
  padding: 3px 12px;
  cursor: pointer;
}
.fab {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 10px 14px calc(10px + env(safe-area-inset-bottom));
  background: linear-gradient(180deg, rgba(244, 247, 245, 0), var(--tc-bg) 40%);
  max-width: 560px;
  margin: 0 auto;
}
</style>
