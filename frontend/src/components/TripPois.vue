<script setup lang="ts">
import { ref, computed } from 'vue'
import { showConfirmDialog, showToast } from 'vant'
import { poiApi, timelineApi, type TripPoi, type Poi } from '../api'
import { nodeIcons } from './icons'
import PositionPicker, { type PosDay } from './PositionPicker.vue'
import PoiPicker from './PoiPicker.vue'

const props = defineProps<{
  tripId: number
  pois: TripPoi[]
  days: PosDay[]
  destCity?: string | null
}>()
const emit = defineEmits<{ (e: 'refresh'): void }>()

// 多城市行程中添加地点时全国搜索，单城市则限定城市
const searchCity = computed(() => {
  const cities = new Set(props.days.map(d => d.city).filter(Boolean))
  return cities.size > 1 ? null : (props.destCity ?? null)
})

const busy = ref(false)

const TYPE_NAMES: Record<string, string> = { hotel: '酒店', attraction: '景点', restaurant: '餐厅', station: '交通' }
const TYPE_COLORS: Record<string, string> = {
  hotel: '#5b7cfa', attraction: '#0e9f6e', restaurant: '#e2872e', station: '#8b5cf6',
}

/* ---------- 地点详情弹窗 ---------- */
const showDetail = ref(false)
const detailPoi = ref<Poi | null>(null)

function openDetail(tp: TripPoi) {
  if (!tp.poi) {
    showToast('该地点尚未关联真实POI')
    return
  }
  detailPoi.value = tp.poi
  showDetail.value = true
}

function insertFromDetail() {
  showDetail.value = false
  picked.value = null
  pickedPoi.value = detailPoi.value
  showPos.value = true
}

/* ---------- 插入指定位置 ---------- */
const showPos = ref(false)
const picked = ref<TripPoi | null>(null)

function openInsert(tp: TripPoi) {
  picked.value = tp
  showPos.value = true
}

/* ---------- 添加地点（搜索真实地点 → 选位置） ---------- */
const showPicker = ref(false)
const pickedPoi = ref<Poi | null>(null)

function openAdd() {
  pickedPoi.value = null
  showPicker.value = true
}

function onPoiSelect(p: Poi) {
  pickedPoi.value = p
  showPos.value = true
}

async function onPosition(choice: { dayNo: number; afterNodeId: number | null; label: string }) {
  const p: Poi | null = picked.value ? picked.value.poi : pickedPoi.value
  if (!p) return
  const dur = p.poi_type === 'hotel' ? 30 : p.poi_type === 'restaurant' ? 90 : 180
  if (busy.value) return
  busy.value = true
  try {
    await timelineApi.addNode(props.tripId, choice.dayNo, {
      node_type: p.poi_type,
      name: p.name,
      duration_minutes: dur,
      poi_id: p.id,
      after_node_id: choice.afterNodeId,
    })
    showToast(`已插入到 ${choice.label}`)
    emit('refresh')
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    busy.value = false
  }
}

/* ---------- 删除（联动轨迹图） ---------- */
async function onDelete(tp: TripPoi) {
  const name = tp.poi?.name || tp.name
  try {
    await showConfirmDialog({
      title: '从行程移除',
      message: `移除「${name}」（第${tp.day_no}天）？`,
    })
  } catch {
    return
  }
  if (busy.value) return
  busy.value = true
  try {
    await poiApi.deleteTrip(props.tripId, tp.node_id)
    showToast('已移除')
    emit('refresh')
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="tpois">
    <div class="tpois-head">
      <span class="tpois-title">行程地点</span>
      <span class="tpois-count">{{ pois.length }}</span>
      <span class="tpois-hint">AI 推荐后可增减感兴趣的地点</span>
      <div class="tpois-actions">
        <button class="tp-btn add" @click="openAdd">＋ 添加地点</button>
      </div>
    </div>

    <div v-if="!pois.length" class="tpois-empty">
      轨迹图中还没有真实地点，点击轨迹图里的占位节点或添加节点即可替换/加入真实酒店、景点、餐厅。
    </div>

    <div v-for="tp in pois" :key="tp.node_id" class="tpois-item">
      <div class="tp-icon" :style="{ color: TYPE_COLORS[tp.poi?.poi_type || tp.node_type], background: (TYPE_COLORS[tp.poi?.poi_type || tp.node_type] || '#999') + '1a' }"
        v-html="nodeIcons[tp.poi?.poi_type || tp.node_type] || ''"></div>
      <div class="tp-main" @click="openDetail(tp)">
        <div class="tp-name-row">
          <span class="tp-name">{{ tp.poi?.name || tp.name }}</span>
          <span class="tp-type">{{ TYPE_NAMES[tp.poi?.poi_type || tp.node_type] || tp.node_type }}</span>
          <span class="tp-day">D{{ tp.day_no }}</span>
        </div>
        <div class="tp-meta">
          <span v-if="tp.poi?.address">{{ tp.poi.address }}</span>
          <span v-if="tp.poi?.phone">{{ tp.poi.phone }}</span>
        </div>
      </div>
      <div class="tp-ops">
        <button class="tp-btn insert" @click="openInsert(tp)">插入</button>
        <button class="tp-btn del" @click="onDelete(tp)">移除</button>
      </div>
    </div>

    <!-- 地点详情弹窗 -->
    <van-popup v-model:show="showDetail" position="bottom" round>
      <div class="sheet" v-if="detailPoi">
        <div class="dt-name">{{ detailPoi.name }}</div>
        <div class="dt-type">{{ TYPE_NAMES[detailPoi.poi_type] }}</div>
        <div class="dt-rows">
          <div v-if="detailPoi.address" class="dt-row"><span class="dt-k">地址</span><span class="dt-v">{{ detailPoi.address }}</span></div>
          <div v-if="detailPoi.phone" class="dt-row"><span class="dt-k">电话</span><span class="dt-v">{{ detailPoi.phone }}</span></div>
          <div v-if="detailPoi.ticket_price" class="dt-row"><span class="dt-k">票价</span><span class="dt-v">{{ detailPoi.ticket_price }}</span></div>
          <div v-if="detailPoi.rating" class="dt-row"><span class="dt-k">评分</span><span class="dt-v">{{ detailPoi.rating }} / 5</span></div>
        </div>
        <van-button type="primary" round block @click="insertFromDetail">插入到行程</van-button>
      </div>
    </van-popup>

    <PositionPicker v-model:show="showPos" :days="days" :default-day-no="days[0]?.day_no ?? 1"
      :title="`插入「${picked ? (picked.poi?.name || picked.name) : pickedPoi?.name ?? ''}」到位置`" @select="onPosition" />
    <PoiPicker v-model:show="showPicker" :city="searchCity"
      title="添加感兴趣的地点（将在选择位置后加入行程）" @select="onPoiSelect" />
  </div>
</template>

<style scoped>
.tpois {
  background: #fff;
  border: 1px solid var(--tc-line);
  border-radius: 14px;
  padding: 12px 14px 14px;
  margin-bottom: 14px;
}
.tpois-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--tc-line);
  flex-wrap: wrap;
}
.tpois-title {
  font-size: 15px;
  font-weight: 800;
  color: var(--tc-ink);
}
.tpois-count {
  font-size: 12px;
  font-weight: 700;
  color: var(--tc-teal-deep);
  background: var(--tc-teal-soft);
  border-radius: 999px;
  padding: 1px 9px;
}
.tpois-hint {
  font-size: 11px;
  color: var(--tc-ink-3);
}.tpois-empty {
  font-size: 12.5px;
  color: var(--tc-ink-3);
  line-height: 1.7;
  padding: 14px 4px;
}
.tpois-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px dashed var(--tc-line);
}
.tp-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.tp-icon :deep(svg) {
  width: 20px;
  height: 20px;
}
.tp-main {
  flex: 1;
  min-width: 0;
}
.tp-name-row {
  display: flex;
  align-items: center;
  gap: 7px;
}
.tp-name {
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tp-type {
  font-size: 10.5px;
  color: var(--tc-ink-3);
  border: 1px solid var(--tc-line);
  border-radius: 6px;
  padding: 0 6px;
  flex: none;
}
.tp-cnt {
  font-size: 10.5px;
  color: var(--tc-orange);
  background: #fceedb;
  border-radius: 6px;
  padding: 0 6px;
  flex: none;
}
.tp-day {
  font-size: 10.5px;
  color: var(--tc-teal-deep);
  background: var(--tc-teal-soft);
  border-radius: 6px;
  padding: 0 6px;
  flex: none;
}
.tp-meta {
  margin-top: 3px;
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--tc-ink-3);
  flex-wrap: wrap;
}
.tp-ops {
  display: flex;
  gap: 6px;
  flex: none;
}
.tp-btn {
  font-size: 12px;
  border-radius: 8px;
  padding: 5px 12px;
  cursor: pointer;
}
.tpois-actions {
  margin-left: auto;
}
.tp-btn.add {
  color: #fff;
  background: var(--tc-teal);
  border: 1px solid var(--tc-teal);
  font-weight: 600;
}
.tp-btn.insert {
  color: var(--tc-teal);
  border: 1px solid var(--tc-teal);
  background: #fff;
}
.tp-btn.del {
  color: #c94f4a;
  border: 1px solid #f0cfcd;
  background: #fff;
}

/* 详情弹窗 */
.sheet {
  padding: 20px 18px 24px;
}
.dt-name {
  font-size: 18px;
  font-weight: 800;
  color: var(--tc-ink);
  text-align: center;
}
.dt-type {
  font-size: 12px;
  color: var(--tc-ink-3);
  text-align: center;
  margin-top: 4px;
  margin-bottom: 14px;
}
.dt-rows {
  border-top: 1px solid var(--tc-line);
  margin-bottom: 16px;
}
.dt-row {
  display: flex;
  padding: 10px 0;
  border-bottom: 1px dashed var(--tc-line);
  font-size: 13.5px;
}
.dt-k {
  width: 56px;
  color: var(--tc-ink-3);
  flex: none;
}
.dt-v {
  flex: 1;
  color: var(--tc-ink);
  word-break: break-all;
}
</style>
