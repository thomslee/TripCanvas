<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { shareApi } from '../api'
import TimelineDay from '../components/TimelineDay.vue'

const route = useRoute()
const token = route.params.token as string
const loading = ref(true)
const tripData = ref<any>(null)
const error = ref('')

onMounted(async () => {
  try {
    const { data } = await shareApi.get(token)
    tripData.value = data
  } catch (e: any) {
    if (e.response?.status === 410) {
      error.value = '分享链接已过期'
    } else if (e.response?.status === 404) {
      error.value = '分享链接不存在'
    } else {
      error.value = '加载失败'
    }
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="share-page">
    <div v-if="loading" class="share-loading">加载中…</div>
    <div v-else-if="error" class="share-error">
      <div class="error-icon">📋</div>
      <div class="error-text">{{ error }}</div>
      <div class="error-sub">链接可能已过期或被删除</div>
    </div>
    <template v-else-if="tripData">
      <div class="share-header">
        <div class="share-brand">途迹 TripCanvas</div>
        <div class="share-title">{{ tripData.title }}</div>
        <div class="share-meta">
          {{ tripData.dest_city }} · {{ tripData.total_days }}天
          <span v-if="tripData.depart_date"> · {{ tripData.depart_date.slice(5).replace('-', '/') }}</span>
        </div>
      </div>

      <div class="share-days">
        <TimelineDay
          v-for="d in tripData.days"
          :key="d.day_no"
          :day="d"
          :trip-id="tripData.trip_id"
          :readonly="true"
        />
      </div>

      <div class="share-footer">
        <div>来自「途迹 TripCanvas」</div>
        <div class="footer-sub">智能旅游行程规划</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.share-page {
  min-height: 100vh;
  background: var(--tc-bg, #f4f6f5);
  padding-bottom: 40px;
}
.share-loading {
  text-align: center;
  padding: 100px 20px;
  color: var(--tc-ink-3, #9ca3af);
  font-size: 14px;
}
.share-error {
  text-align: center;
  padding: 100px 20px;
}
.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.error-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--tc-ink, #1a1b1c);
}
.error-sub {
  margin-top: 6px;
  font-size: 12px;
  color: var(--tc-ink-3, #9ca3af);
}
.share-header {
  background: linear-gradient(135deg, #0e9f6e 0%, #057a55 100%);
  color: #fff;
  padding: 32px 20px 24px;
  text-align: center;
}
.share-brand {
  font-size: 12px;
  opacity: 0.85;
  letter-spacing: 2px;
}
.share-title {
  margin-top: 8px;
  font-size: 22px;
  font-weight: 800;
}
.share-meta {
  margin-top: 6px;
  font-size: 13px;
  opacity: 0.9;
}
.share-days {
  padding: 16px 14px;
  max-width: 600px;
  margin: 0 auto;
}
.share-footer {
  text-align: center;
  padding: 24px 20px;
  color: var(--tc-ink-3, #9ca3af);
  font-size: 12px;
}
.footer-sub {
  margin-top: 4px;
  font-size: 11px;
  opacity: 0.7;
}
</style>
