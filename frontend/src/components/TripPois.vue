<script setup lang="ts">
import { ref } from 'vue'
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

const busy = ref(false)

const TYPE_NAMES: Record<string, string> = { hotel: '酒店', attraction: '景点', restaurant: '餐厅' }
const TYPE_COLORS: Record<string, string> = {
  hotel: '#5b7cfa', attraction: '#0e9f6e', restaurant: '#e2872e',
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
  try {
    await showConfirmDialog({
      title: '从行程移除',
      message: `移除「${tp.poi.name}」？轨迹图中对应 ${tp.count} 个节点将一并删除。`,
    })
  } catch {
    return
  }
  if (busy.value) return
  busy.value = true
  try {
    await poiApi.deleteTrip(props.tripId, tp.poi.id)
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
      <span class="tpois-title">行程真实地点</span>
      <span class="tpois-count">{{ pois.length }}</span>
      <span class="tpois-hint">AI 推荐后可增减感兴趣的地点</span>
      <div class="tpois-actions">
        <button class="tp-btn add" @click="openAdd">＋ 添加地点</button>
      </div>
    </div>

    <div v-if="!pois.length" class="tpois-empty">
      轨迹图中还没有真实地点，点击轨迹图里的占位节点或添加节点即可替换/加入真实酒店、景点、餐厅。
    </div>

    <div v-for="tp in pois" :key="tp.poi.id" class="tpois-item">
      <div class="tp-icon" :style="{ color: TYPE_COLORS[tp.poi.poi_type], background: TYPE_COLORS[tp.poi.poi_type] + '1a' }"
        v-html="nodeIcons[tp.poi.poi_type] || ''"></div>
      <div class="tp-main">
        <div class="tp-name-row">
          <span class="tp-name">{{ tp.poi.name }}</span>
          <span class="tp-type">{{ TYPE_NAMES[tp.poi.poi_type] }}</span>
          <span v-if="tp.count > 1" class="tp-cnt">×{{ tp.count }}</span>
        </div>
        <div class="tp-meta">
          <span v-if="tp.poi.open_hours">营业 {{ tp.poi.open_hours }}</span>
          <span v-if="tp.poi.ticket_price">{{ tp.poi.ticket_price }}</span>
        </div>
      </div>
      <div class="tp-ops">
        <button class="tp-btn insert" @click="openInsert(tp)">插入</button>
        <button class="tp-btn del" @click="onDelete(tp)">移除</button>
      </div>
    </div>

    <PositionPicker v-model:show="showPos" :days="days" :default-day-no="days[0]?.day_no ?? 1"
      :title="`插入「${picked ? picked.poi.name : pickedPoi?.name ?? ''}」到位置`" @select="onPosition" />
    <PoiPicker v-model:show="showPicker" :city="destCity"
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
</style>
