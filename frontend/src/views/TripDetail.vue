<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import html2canvas from 'html2canvas'
import { tripsApi, timelineApi, poiApi, weatherApi, replanApi,
  type Timeline, type TripPoi, type Weather } from '../api'
import TimelineDay from '../components/TimelineDay.vue'
import TripPois from '../components/TripPois.vue'
import type { PosDay } from '../components/PositionPicker.vue'
import { weatherIcons } from '../components/icons'

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

const dateRange = computed(() => {
  const days = timeline.value?.days ?? []
  if (!days.length) return ''
  const fmt = (d: string) => d.slice(5).replace('-', '/')
  return `${fmt(days[0].date ?? '')} - ${fmt(days[days.length - 1].date ?? '')}`
})

async function load() {
  try {
    const tl = await timelineApi.get(tripId)
    const hasContent = tl.data.days.some((d) => d.nodes.length > 0)
    if (!hasContent) {
      await timelineApi.seed(tripId)
      const tl2 = await timelineApi.get(tripId)
      timeline.value = tl2.data
    } else {
      timeline.value = tl.data
    }
    title.value = tl.data.title ?? ''
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

async function onDelete() {
  try {
    await showConfirmDialog({ title: '删除行程', message: '确定删除该行程吗？' })
  } catch {
    return
  }
  try {
    await tripsApi.remove(tripId)
    showToast('已删除')
    router.replace('/')
  } catch (e) {
    showToast((e as Error).message)
  }
}

/* ---------- 导出：复制文本 + 保存长图 ---------- */
const TRANSPORT_NAMES: Record<string, string> = {
  plane: '飞机', train: '火车', ship: '轮船', car: '自驾',
  taxi: '打车', bus: '公交', metro: '地铁', bike: '自行车', walk: '步行',
}
const NODE_TYPE_NAMES: Record<string, string> = {
  hotel: '酒店', attraction: '景点', restaurant: '餐厅', transfer: '交通',
}

function fmtDur(min: number): string {
  if (min >= 60) {
    const h = Math.floor(min / 60)
    const m = min % 60
    return m ? `${h}h${m}m` : `${h}h`
  }
  return `${min}m`
}

function buildTripText(): string {
  if (!timeline.value) return ''
  const lines: string[] = []
  lines.push(title.value)
  lines.push(`${timeline.value.dest_city} · ${dateRange.value} · ${timeline.value.days.length}天`)
  lines.push('')
  for (const day of timeline.value.days) {
    const cityTag = day.city ? ` ${day.city}` : ''
    lines.push(`D${day.day_no}${cityTag}（${day.date}） ${day.window_start}-${day.window_end}`)
    for (const node of day.nodes) {
      const st = node.start_time ? node.start_time.slice(0, 5) : '--:--'
      const type = NODE_TYPE_NAMES[node.node_type] ?? node.node_type
      lines.push(`  ${st} ${node.name}（${type}）${fmtDur(node.duration_minutes)}`)
      const edge = day.edges.find((e) => e.from_node_id === node.id)
      if (edge) {
        const t = TRANSPORT_NAMES[edge.transport] ?? edge.transport
        lines.push(`    ↓ ${t} ${edge.duration_minutes}m`)
      }
    }
    lines.push('')
  }
  return lines.join('\n')
}

async function copyTripText() {
  const text = buildTripText()
  try {
    await navigator.clipboard.writeText(text)
    showToast('行程已复制到剪贴板')
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    showToast('行程已复制')
  }
}

const exportRef = ref<HTMLElement | null>(null)
const exporting = ref(false)

async function saveLongImage() {
  if (!exportRef.value || exporting.value) return
  exporting.value = true
  try {
    const canvas = await html2canvas(exportRef.value, {
      backgroundColor: '#f4f6f5',
      scale: 2,
      useCORS: true,
      logging: false,
    })
    const link = document.createElement('a')
    link.download = `${title.value || '行程'}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
    showToast('长图已保存')
  } catch {
    showToast('保存失败，请重试')
  } finally {
    exporting.value = false
  }
}

onMounted(load)

const posDays = ref<PosDay[]>([])

watch(
  timeline,
  (tl) => {
    posDays.value = (tl?.days ?? []).map((d) => ({
      day_no: d.day_no,
      date: d.date,
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
      <div ref="exportRef">
      <div class="tc-card trip-head">
        <div class="head-row1">
          <span class="head-title">{{ title }}</span>
          <span class="badge">草稿</span>
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
          <button class="ai-btn" :disabled="replanning" @click="onReplan">
            {{ replanning ? '规划中…' : 'AI 规划' }}
          </button>
          <button class="del-btn" @click="onDelete">删除行程</button>
        </div>
        <div class="export-row">
          <button class="export-btn" @click="copyTripText">复制行程</button>
          <button class="export-btn" :disabled="exporting" @click="saveLongImage">
            {{ exporting ? '生成中…' : '保存长图' }}
          </button>
        </div>
        <div class="hint">
          先看上方真实地点清单，再在下方轨迹图中调整；点占位节点可替换为真实地点，点「真实」节点查看营业时间/票价等。
        </div>
      </div>

      <TripPois :trip-id="tripId" :pois="tripPois" :days="posDays" :dest-city="timeline.dest_city ?? null"
        @refresh="refresh" />

      <TimelineDay v-for="d in timeline.days" :key="d.day_no" :day="d" :trip-id="tripId"
        :dest-city="timeline.dest_city ?? null" @refresh="refresh" />
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
    </template>
  </div>
</template>

<style scoped>
.badge {
  font-size: 11px;
  padding: 2px 9px;
  border-radius: 999px;
  background: var(--tc-teal-soft);
  color: var(--tc-teal-deep);
  flex: none;
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
</style>
