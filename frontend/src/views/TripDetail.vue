<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { timelineApi, poiApi, weatherApi, replanApi, aiPlanApi, autoReplaceApi, recalcTransportApi, shareApi, tripsApi,
  type Timeline, type TripPoi, type Weather } from '../api'
import TimelineDay from '../components/TimelineDay.vue'
import TripPois from '../components/TripPois.vue'
import type { PosDay } from '../components/PositionPicker.vue'
import { weatherIcons } from '../components/icons'
import { exportTripToPDF } from '../utils/pdfExport'

const route = useRoute()
const router = useRouter()

const tripId = Number(route.params.id)
const title = ref('')
const timeline = ref<Timeline | null>(null)
const tripPois = ref<TripPoi[]>([])
const loading = ref(true)
const weatherMap = ref<Record<string, Weather>>({})
const weatherLoading = ref(false)
const weatherFail = ref<string[]>([])

/* ---------- 行程状态（定稿） ---------- */
const STATUS_TEXT: Record<string, string> = {
  draft: '草稿',
  planning: '规划中',
  active: '进行中',
  done: '已完成',
  finalized: '已定稿',
}
const tripStatus = ref('draft')
const finalizing = ref(false)

async function loadTripStatus() {
  try {
    const { data } = await tripsApi.get(tripId)
    tripStatus.value = data.status
  } catch {
    /* 状态获取失败不阻塞详情加载 */
  }
}

async function onFinalize() {
  if (finalizing.value) return
  finalizing.value = true
  try {
    const { data } = await tripsApi.finalize(tripId)
    tripStatus.value = data.status
    showToast('行程已定稿，可在途迹记忆中同步')
  } catch (e) {
    showToast((e as Error).message || '定稿失败')
  } finally {
    finalizing.value = false
  }
}

async function onUnfinalize() {
  if (finalizing.value) return
  finalizing.value = true
  try {
    const { data } = await tripsApi.unfinalize(tripId)
    tripStatus.value = data.status
    showToast('已取消定稿，恢复为草稿')
  } catch (e) {
    showToast((e as Error).message || '操作失败')
  } finally {
    finalizing.value = false
  }
}

/* ---------- 行程城市（天气按城市动态生成卡片） ---------- */
const cities = computed(() => {
  const set = new Set<string>()
  ;(timeline.value?.days ?? []).forEach((d) => {
    if (d.city) set.add(d.city)
  })
  return [...set]
})

async function loadWeather(city: string) {
  try {
    const { data } = await weatherApi.get(city)
    if (data.available) {
      weatherMap.value = { ...weatherMap.value, [city]: data }
      weatherFail.value = weatherFail.value.filter((c) => c !== city)
    } else {
      weatherFail.value = [...new Set([...weatherFail.value, city])]
    }
  } catch {
    weatherFail.value = [...new Set([...weatherFail.value, city])]
  }
}

async function loadWeatherAll() {
  if (!cities.value.length) return
  weatherLoading.value = true
  await Promise.all(cities.value.map(loadWeather))
  weatherLoading.value = false
}

/* ---------- AI 二次推荐 ---------- */
const replanning = ref(false)
const showNotes = ref(false)
const replanSummary = ref('')
const replanNotes = ref<string[]>([])

async function onReplan() {
  if (replanning.value) return
  replanning.value = true
  try {
    const { data } = await replanApi.run(tripId)
    timeline.value = data.timeline
    title.value = data.timeline.title ?? ''
    replanSummary.value = data.summary
    replanNotes.value = data.notes ?? []
    showNotes.value = true
    await loadPois()
    showToast(data.summary)
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    replanning.value = false
  }
}

/* ---------- AI 生成行程 ---------- */
const aiPlanning = ref(false)

async function onAIPlan() {
  if (aiPlanning.value) return
  aiPlanning.value = true
  try {
    const { data } = await aiPlanApi.run(tripId)
    timeline.value = data.timeline
    title.value = data.timeline.title ?? ''
    await loadWeatherAll()
    await loadPois()
    showToast(`AI 已生成 ${data.total_nodes} 个节点`)
  } catch (e) {
    showToast((e as Error).message || 'AI 生成失败')
  } finally {
    aiPlanning.value = false
  }
}

async function onSeed() {
  try {
    await timelineApi.seed(tripId)
    await refresh()
    showToast('已生成默认骨架')
  } catch (e) {
    showToast((e as Error).message)
  }
}

const hasNodes = computed(() => {
  return (timeline.value?.days ?? []).some((d) => d.nodes.length > 0)
})

/* ---------- 一键替换为高德真实地点 ---------- */
const autoReplacing = ref(false)

async function onAutoReplace() {
  if (autoReplacing.value) return
  autoReplacing.value = true
  try {
    const { data } = await autoReplaceApi.run(tripId)
    timeline.value = data.timeline
    title.value = data.timeline.title ?? ''
    await loadPois()
    if (data.failed > 0) {
      showToast(`已替换 ${data.replaced} 个，${data.failed} 个未找到可手动替换`)
    } else {
      showToast(`已一键替换 ${data.replaced} 个真实地点`)
    }
  } catch (e) {
    showToast((e as Error).message || '替换失败')
  } finally {
    autoReplacing.value = false
  }
}

/* ---------- 交通规划：重新计算所有边的交通方式、距离、用时 ---------- */
const recalcLoading = ref(false)

async function onRecalcTransport() {
  if (recalcLoading.value) return
  recalcLoading.value = true
  try {
    const { data } = await recalcTransportApi.run(tripId)
    timeline.value = data.timeline
    title.value = data.timeline.title ?? ''
    showToast(`已重新规划 ${data.updated} 段交通`)
  } catch (e) {
    showToast((e as Error).message || '交通规划失败')
  } finally {
    recalcLoading.value = false
  }
}

/* ---------- PDF导出：每天一页 ---------- */
const pdfExporting = ref(false)

async function onExportPDF() {
  if (pdfExporting.value || !timeline.value) return
  pdfExporting.value = true
  try {
    // 获取每天的TimelineDay元素
    const dayElements = document.querySelectorAll('.timeline-day-card')
    if (!dayElements.length) {
      showToast('暂无行程数据')
      return
    }
    const elements = Array.from(dayElements) as HTMLElement[]
    const filename = `${timeline.value.title || '行程'}_${new Date().toISOString().slice(0, 10)}.pdf`
    await exportTripToPDF(timeline.value.title || '行程', elements, filename)
    showToast('PDF已导出')
  } catch (e) {
    showToast('PDF导出失败')
    console.error(e)
  } finally {
    pdfExporting.value = false
  }
}

/* ---------- 分享：生成链接+海报 ---------- */
const showShare = ref(false)
const shareLoading = ref(false)
const shareUrl = ref('')
const shareExpires = ref('')

async function openShare() {
  showShare.value = true
  if (!shareUrl.value) {
    await generateShareLink()
  }
}

async function generateShareLink() {
  shareLoading.value = true
  try {
    const { data } = await shareApi.create(tripId)
    const baseUrl = window.location.origin
    shareUrl.value = `${baseUrl}/share/${data.token}`
    shareExpires.value = new Date(data.expires_at).toLocaleDateString('zh-CN')
  } catch (e) {
    showToast('生成分享链接失败')
  } finally {
    shareLoading.value = false
  }
}

async function copyShareLink() {
  const text = shareUrl.value
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      // 降级方案：用textarea + execCommand
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.cssText = 'position:fixed;left:-9999px;top:0;'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    showToast('链接已复制，7天内有效')
  } catch {
    showToast('复制失败，请长按链接手动复制')
  }
}

const dateRange = computed(() => {
  const days = timeline.value?.days ?? []
  if (!days.length) return ''
  const fmt = (d: string) => d.slice(5).replace('-', '/')
  return `${fmt(days[0].date ?? '')} - ${fmt(days[days.length - 1].date ?? '')}`
})

async function load() {
  try {
    const tl = await timelineApi.get(tripId)
    timeline.value = tl.data
    title.value = tl.data.title ?? ''
    await loadTripStatus()
    await loadWeatherAll()
    await loadPois()
  } catch (e) {
    showToast((e as Error).message)
    router.replace('/')
  } finally {
    loading.value = false
  }
}

async function loadPois() {
  try {
    const { data } = await poiApi.listTrip(tripId)
    tripPois.value = data
  } catch {
    tripPois.value = []
  }
}

async function refresh() {
  try {
    const { data } = await timelineApi.get(tripId)
    timeline.value = data
    title.value = data.title ?? ''
  } catch (e) {
    showToast((e as Error).message)
  }
  await loadPois()
}

/* ---------- 导出：复制文本 + 保存长图 ---------- */
onMounted(load)

const posDays = ref<PosDay[]>([])

watch(
  timeline,
  (tl) => {
    posDays.value = (tl?.days ?? []).map((d) => ({
      day_no: d.day_no,
      date: d.date,
      city: d.city || undefined,
      nodes: d.nodes.map((n) => ({ id: n.id, name: n.name })),
    }))
  },
  { immediate: true },
)
</script>

<template>
  <div class="tc-page">
    <van-nav-bar title="行程详情" left-arrow @click-left="router.back()" fixed placeholder />

    <van-loading v-if="loading" style="padding: 60px 0" color="#0e7c7e" vertical>加载中…</van-loading>

    <template v-else-if="timeline">
      <!-- 空态：还没有行程节点 -->
      <div v-if="!hasNodes" class="empty-plan">
        <div class="empty-icon">
          <svg width="56" height="56" viewBox="0 0 24 24" fill="none">
            <path d="M12 21s-7-5.2-7-11a7 7 0 1 1 14 0c0 5.8-7 11-7 11Z" stroke="#0e7c7e" stroke-width="1.5" stroke-linejoin="round"/>
            <circle cx="12" cy="10" r="2.5" stroke="#0e7c7e" stroke-width="1.5"/>
          </svg>
        </div>
        <div class="empty-title">开始规划这段行程</div>
        <div class="empty-desc">AI 将根据目的地、航班时间和偏好，智能生成每日景点、餐厅和酒店安排</div>
        <div class="empty-actions">
          <button class="ai-generate-btn" :disabled="aiPlanning" @click="onAIPlan">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2a10 10 0 1 0 10 10H12V2z"/><path d="M20 2v10h-10"/>
            </svg>
            {{ aiPlanning ? 'AI 正在生成…' : 'AI 生成行程' }}
          </button>
          <button class="seed-btn" @click="onSeed">生成默认骨架</button>
        </div>
        <div v-if="aiPlanning" class="ai-loading-hint">大模型正在规划中，通常需要 5-15 秒…</div>
      </div>

      <div v-else>
      <div class="tc-card trip-head">
        <div class="head-row1">
          <span class="head-title">{{ title }}</span>
          <span class="badge" :class="tripStatus">{{ STATUS_TEXT[tripStatus] || tripStatus }}</span>
        </div>
        <div class="head-route">
          {{ timeline.dest_city }} · {{ dateRange }} · {{ timeline.days.length }}天
        </div>
        <div class="weather-row">
          <div v-if="weatherLoading && !cities.length" class="wx-loading">天气加载中…</div>
          <div v-for="city in cities" :key="city" class="wx-card">
            <template v-if="weatherFail.includes(city) && !weatherMap[city]">
              <span class="wx-ico" v-html="weatherIcons['cloud']"></span>
              <div class="wx-main">
                <div class="wx-desc">{{ city }}</div>
                <div class="wx-fail">天气暂不可用</div>
              </div>
            </template>
            <template v-else-if="weatherMap[city]">
              <span class="wx-ico" v-html="weatherIcons[weatherMap[city].icon] || weatherIcons['cloud']"></span>
              <div class="wx-main">
                <div class="wx-desc">{{ city }} · 今天 {{ weatherMap[city].desc }}</div>
                <div class="wx-temp">
                  {{ weatherMap[city].temp }}°<span class="wx-feels">体感 {{ weatherMap[city].feels }}°</span>
                  <span v-if="weatherMap[city].temp_max != null" class="wx-range">
                    {{ weatherMap[city].temp_min }}° ~ {{ weatherMap[city].temp_max }}°
                  </span>
                </div>
                <div v-if="weatherMap[city].advice" class="wx-advice">穿衣：{{ weatherMap[city].advice }}</div>
                <div v-if="weatherMap[city].forecast?.length" class="wx-fc">
                  <div v-for="f in weatherMap[city].forecast" :key="f.date" class="wx-fc-item">
                    <span class="fc-date">{{ f.date }}</span>
                    <span class="fc-ico" v-html="weatherIcons[f.icon] || weatherIcons['cloud']"></span>
                    <span class="fc-desc">{{ f.desc }}</span>
                    <span class="fc-temp">{{ f.temp_min }}°~{{ f.temp_max }}°</span>
                  </div>
                </div>
              </div>
            </template>
            <template v-else>
              <span class="wx-ico" v-html="weatherIcons['cloud']"></span>
              <div class="wx-main">
                <div class="wx-desc">{{ city }}</div>
                <div class="wx-loading">天气加载中…</div>
              </div>
            </template>
          </div>
        </div>
        <div class="op-row">
          <button v-if="tripStatus !== 'finalized'" class="ai-btn" :disabled="finalizing" @click="onFinalize">
            {{ finalizing ? '定稿中…' : '行程定稿' }}
          </button>
          <button v-else class="export-btn" :disabled="finalizing" @click="onUnfinalize">
            {{ finalizing ? '处理中…' : '取消定稿' }}
          </button>
          <button class="ai-btn" :disabled="replanning" @click="onReplan">
            {{ replanning ? '优化中…' : 'AI 优化' }}
          </button>
          <button class="replace-btn" :disabled="autoReplacing" @click="onAutoReplace">
            {{ autoReplacing ? '校正中…' : '地点校正' }}
          </button>
          <button class="replace-btn" :disabled="recalcLoading" @click="onRecalcTransport">
            {{ recalcLoading ? '计算中…' : '交通规划' }}
          </button>
        </div>
        <div class="export-row">
          <button class="export-btn" :disabled="pdfExporting" @click="onExportPDF">
            {{ pdfExporting ? '导出中…' : '导出PDF' }}
          </button>
          <button class="export-btn" @click="openShare">分享</button>
        </div>
        <div class="hint">
          先看上方真实地点清单，再在下方轨迹图中调整；点占位节点可替换为真实地点，点「真实」节点查看营业时间/票价等。
        </div>
      </div>

      <TripPois :trip-id="tripId" :pois="tripPois" :days="posDays" :dest-city="timeline.dest_city ?? null"
        @refresh="refresh" />

      <TimelineDay v-for="d in timeline.days" :key="d.day_no" :day="d" :trip-id="tripId"
        :dest-city="d.city || timeline.dest_city || null" @refresh="refresh" />
      </div>

      <van-popup v-model:show="showNotes" position="bottom" round>
        <div class="notes-panel">
          <div class="notes-title">{{ replanSummary }}</div>
          <div class="notes-sub">依据评分、类型分布与营业时间对现有地点重排，未增删你的地点与时长</div>
          <div v-if="replanNotes.length" class="notes-list">
            <div v-for="(n, i) in replanNotes" :key="i" class="notes-item">
              <span class="notes-dot"></span>{{ n }}
            </div>
          </div>
          <div v-else class="notes-empty">没有需要调整的项，当前行程已是最优。</div>
          <button class="notes-close" @click="showNotes = false">知道了</button>
        </div>
      </van-popup>

      <!-- 分享弹窗 -->
      <van-popup v-model:show="showShare" position="bottom" round>
        <div class="share-panel">
          <div class="share-title">分享行程</div>
          <div class="share-desc">生成只读链接，好友无需登录即可查看，7天内有效</div>
          <div v-if="shareLoading" class="share-loading">生成中…</div>
          <div v-else-if="shareUrl" class="share-link-box">
            <div class="share-url" style="user-select:text;cursor:text;">{{ shareUrl }}</div>
            <div class="share-expire">有效期至 {{ shareExpires }}</div>
            <button class="share-copy-btn" @click="copyShareLink">复制链接</button>
          </div>
          <div v-else class="share-loading">生成失败，请重试</div>
          <button class="share-close" @click="showShare = false">关闭</button>
        </div>
      </van-popup>
    </template>
  </div>
</template>

<style scoped>
.empty-plan {
  text-align: center;
  padding: 50px 20px 40px;
}
.empty-icon {
  margin-bottom: 16px;
  opacity: 0.7;
}
.empty-title {
  font-size: 18px;
  font-weight: 700;
  color: #1a2a27;
  margin-bottom: 8px;
}
.empty-desc {
  font-size: 13px;
  color: #7a8a87;
  line-height: 1.6;
  max-width: 280px;
  margin: 0 auto 24px;
}
.empty-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 280px;
  margin: 0 auto;
}
.ai-generate-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 13px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #0e7c7e, #12a5a8);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(14, 124, 126, 0.3);
}
.ai-generate-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.seed-btn {
  padding: 11px;
  border: 1px solid #d8e0de;
  background: #fff;
  color: #5a6a67;
  font-size: 14px;
  font-weight: 600;
  border-radius: 12px;
  cursor: pointer;
}
.ai-loading-hint {
  margin-top: 16px;
  font-size: 12px;
  color: #0e7c7e;
  font-weight: 600;
}
.badge {
  font-size: 11px;
  padding: 2px 9px;
  border-radius: 999px;
  background: var(--tc-teal-soft);
  color: var(--tc-teal-deep);
  flex: none;
}
.badge.finalized {
  background: #fff3e0;
  color: #e65100;
}
.head-row1 {
  display: flex;
  align-items: center;
  gap: 8px;
}
.head-title {
  font-size: 16px;
  font-weight: 700;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.head-route {
  margin-top: 4px;
  font-size: 12.5px;
  color: var(--tc-ink-2);
}
.weather-row {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.wx-card {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background: linear-gradient(135deg, rgba(14, 124, 126, 0.08), rgba(14, 124, 126, 0.16));
  border: 1px solid rgba(14, 124, 126, 0.18);
  border-radius: 12px;
  padding: 8px 12px;
  width: 100%;
  box-sizing: border-box;
}
.op-row {
  margin-top: 10px;
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.export-row {
  margin-top: 8px;
  display: flex;
  gap: 10px;
  align-items: center;
}
.export-btn {
  flex: 1;
  border: 1px solid var(--tc-teal);
  background: #fff;
  color: var(--tc-teal-deep);
  font-size: 12.5px;
  font-weight: 600;
  border-radius: 8px;
  padding: 5px 0;
  cursor: pointer;
}
.export-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.wx-ico {
  color: var(--tc-teal-deep);
  display: flex;
  flex: none;
  margin-top: 2px;
}
.wx-ico :deep(svg) {
  width: 26px;
  height: 26px;
}
.wx-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.wx-desc {
  font-size: 11.5px;
  color: var(--tc-ink-2);
}
.wx-temp {
  font-size: 15px;
  font-weight: 800;
  color: var(--tc-ink);
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}
.wx-feels {
  font-size: 10.5px;
  font-weight: 400;
  color: var(--tc-ink-3);
}
.wx-range {
  font-size: 11px;
  font-weight: 600;
  color: var(--tc-teal-deep);
}
.wx-advice {
  font-size: 11.5px;
  color: var(--tc-teal-deep);
  line-height: 1.5;
}
.wx-fc {
  margin-top: 6px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.wx-fc-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(14, 124, 126, 0.14);
  border-radius: 9px;
  padding: 5px 9px;
  min-width: 58px;
}
.fc-date {
  font-size: 10.5px;
  font-weight: 700;
  color: var(--tc-ink-2);
}
.fc-ico {
  color: var(--tc-teal-deep);
  display: flex;
}
.fc-ico :deep(svg) {
  width: 16px;
  height: 16px;
}
.fc-desc {
  font-size: 10px;
  color: var(--tc-ink-2);
}
.fc-temp {
  font-size: 10.5px;
  font-weight: 700;
  color: var(--tc-ink);
}
.wx-loading {
  font-size: 12px;
  color: var(--tc-ink-3);
  padding: 8px 0;
}
.wx-fail {
  font-size: 12px;
  color: var(--tc-ink-3);
  padding: 8px 0;
}
.ai-btn {
  border: 1px solid var(--tc-teal);
  background: var(--tc-teal);
  color: #fff;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: 8px;
  padding: 5px 16px;
  cursor: pointer;
  flex: none;
}
.ai-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.replace-btn {
  border: 1px solid #1677ff;
  background: #1677ff;
  color: #fff;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: 8px;
  padding: 5px 14px;
  cursor: pointer;
  flex: none;
}
.replace-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.hint {
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--tc-ink-3);
  background: var(--tc-bg);
  border-radius: 10px;
  padding: 8px 10px;
}
.del-btn {
  border: 1px solid #f0cfcd;
  background: #fff;
  color: #c94f4a;
  font-size: 12px;
  border-radius: 8px;
  padding: 4px 12px;
  cursor: pointer;
  flex: none;
}
.notes-panel {
  padding: 18px 16px 20px;
}
.notes-title {
  font-size: 15px;
  font-weight: 800;
  color: var(--tc-ink);
}
.notes-sub {
  margin-top: 3px;
  font-size: 11.5px;
  color: var(--tc-ink-3);
}
.notes-list {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 9px;
  max-height: 46vh;
  overflow: auto;
}
.notes-item {
  display: flex;
  gap: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--tc-ink-2);
  background: var(--tc-bg);
  border-radius: 9px;
  padding: 9px 11px;
}
.notes-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--tc-teal);
  flex: none;
  margin-top: 7px;
}
.notes-empty {
  margin-top: 14px;
  font-size: 13px;
  color: var(--tc-ink-3);
  text-align: center;
  padding: 16px 0;
}
.notes-close {
  margin-top: 14px;
  width: 100%;
  border: none;
  background: var(--tc-teal);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  border-radius: 10px;
  padding: 10px 0;
  cursor: pointer;
}
.share-panel {
  padding: 20px 16px 24px;
}
.share-title {
  font-size: 16px;
  font-weight: 800;
  color: var(--tc-ink);
  text-align: center;
}
.share-desc {
  margin-top: 6px;
  font-size: 12px;
  color: var(--tc-ink-3);
  text-align: center;
}
.share-loading {
  margin-top: 20px;
  text-align: center;
  font-size: 13px;
  color: var(--tc-ink-3);
  padding: 20px 0;
}
.share-link-box {
  margin-top: 16px;
  background: var(--tc-bg);
  border-radius: 10px;
  padding: 12px;
}
.share-url {
  font-size: 12px;
  color: var(--tc-ink);
  word-break: break-all;
  line-height: 1.5;
}
.share-expire {
  margin-top: 6px;
  font-size: 11px;
  color: var(--tc-orange);
}
.share-copy-btn {
  margin-top: 10px;
  width: 100%;
  border: none;
  background: var(--tc-teal);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  border-radius: 8px;
  padding: 8px 0;
  cursor: pointer;
}
.share-close {
  margin-top: 14px;
  width: 100%;
  border: 1px solid var(--tc-line);
  background: #fff;
  color: var(--tc-ink-3);
  font-size: 13px;
  border-radius: 10px;
  padding: 9px 0;
  cursor: pointer;
}
.poster-panel {
  padding: 16px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}
.poster-title {
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--tc-ink);
  margin-bottom: 12px;
}
.poster-img-wrap {
  flex: 1;
  overflow-y: auto;
  text-align: center;
  background: var(--tc-bg);
  border-radius: 8px;
  padding: 8px;
}
.poster-img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0 auto;
}
.poster-close {
  margin-top: 12px;
  width: 100%;
  border: 1px solid var(--tc-line);
  background: #fff;
  color: var(--tc-ink-3);
  font-size: 14px;
  border-radius: 10px;
  padding: 10px 0;
  cursor: pointer;
}
</style>
