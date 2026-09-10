<script setup lang="ts">
import { ref } from 'vue'
import { showConfirmDialog, showToast } from 'vant'
import { timelineApi, type DayTimeline, type ItineraryNode, type ItineraryEdge, type Transport, type NodeType, type Poi } from '../api'
import { nodeIcons, transportIcons } from './icons'
import PoiPicker from './PoiPicker.vue'
import PositionPicker, { type PosDay } from './PositionPicker.vue'

const props = defineProps<{ day: DayTimeline; tripId: number; destCity?: string | null }>()
const emit = defineEmits<{ (e: 'refresh'): void }>()

const busy = ref(false)

const TRANSPORT_NAMES: Record<string, string> = {
  plane: '飞机', train: '火车', ship: '轮船', car: '自驾',
  taxi: '打车', bus: '公交', metro: '地铁', bike: '自行车', walk: '步行',
}
const NODE_TYPE_NAMES: Record<string, string> = { hotel: '酒店', attraction: '景点', restaurant: '餐厅', station: '交通' }
const NODE_TYPE_COLORS: Record<string, string> = {
  hotel: '#5b7cfa', attraction: '#0e9f6e', restaurant: '#e2872e', station: '#8b5cf6',
}

function fmtDur(m: number): string {
  const h = Math.floor(m / 60)
  const mm = m % 60
  if (h && mm) return `${h}h${mm}m`
  if (h) return `${h}h`
  return `${mm}m`
}

/** 真实 POI：有关联且来源为内置/高德（有详细信息） */
function isRealPoi(node: ItineraryNode): boolean {
  return !!(node.poi && (node.poi.source === 'gaode' || node.poi.source === 'seed'))
}
/** AI 推荐 POI：AI 生成的自定义 POI（有名称但无详细信息） */
function isAiPoi(node: ItineraryNode): boolean {
  return !!(node.poi && node.poi.source === 'ai')
}

function fmtOverflow(m: number): string {
  const h = Math.floor(m / 60)
  const mm = m % 60
  if (h && mm) return `${h}h${mm}m`
  if (h) return `${h}h`
  return `${mm}m`
}

async function run(fn: () => Promise<unknown>, toast = '已更新') {
  if (busy.value) return
  busy.value = true
  try {
    await fn()
    showToast(toast)
    emit('refresh')
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    busy.value = false
  }
}

/* ---------- 节点操作 ---------- */
function adjust(node: ItineraryNode, delta: number) {
  const v = Math.max(10, Math.min(1440, node.duration_minutes + delta))
  if (v === node.duration_minutes) return
  run(() => timelineApi.patchNode(node.id, { duration_minutes: v }), `时长 ${fmtDur(v)}`)
}

function move(node: ItineraryNode, dir: 'up' | 'down') {
  run(() => timelineApi.moveNode(node.id, dir), dir === 'up' ? '已上移' : '已下移')
}

async function remove(node: ItineraryNode) {
  try {
    await showConfirmDialog({ title: '删除节点', message: `确定删除「${node.name}」吗？` })
  } catch {
    return
  }
  run(() => timelineApi.deleteNode(node.id), '已删除')
}

/* ---------- 替换为真实地点 ---------- */
const replaceTarget = ref<ItineraryNode | null>(null)
const showReplace = ref(false)

function openReplace(node: ItineraryNode) {
  replaceTarget.value = node
  showReplace.value = true
}

function onReplacePoi(p: Poi) {
  const node = replaceTarget.value
  if (!node) return
  run(() => timelineApi.patchNode(node.id, { poi_id: p.id }), `已替换为「${p.name}」`)
}

/* ---------- 真实地点详情 ---------- */
const detailNode = ref<ItineraryNode | null>(null)
const showDetail = ref(false)

function openDetail(node: ItineraryNode) {
  detailNode.value = node
  showDetail.value = true
}

/* ---------- 交通切换 ---------- */
const showTransport = ref(false)
const activeEdge = ref<ItineraryEdge | null>(null)
const TRANSPORTS: Transport[] = ['walk', 'taxi', 'bus', 'metro', 'bike', 'car', 'train', 'ship', 'plane']

function openTransport(edge: ItineraryEdge) {
  activeEdge.value = edge
  showTransport.value = true
}

function pickTransport(t: Transport) {
  if (!activeEdge.value) return
  const e = activeEdge.value
  showTransport.value = false
  run(() => timelineApi.patchEdge(e.id, { transport: t }), `已切换为${TRANSPORT_NAMES[t]}`)
}

/* ---------- 添加节点：两级流程 ---------- */
const showAddMenu = ref(false)
const showPlaceholder = ref(false)
const showPoiPicker = ref(false)
const showPosition = ref(false)
const pickedPoi = ref<Poi | null>(null)

const ADD_PRESETS: { type: NodeType; duration_minutes: number; desc: string }[] = [
  { type: 'attraction', duration_minutes: 180, desc: '默认 3 小时' },
  { type: 'restaurant', duration_minutes: 90, desc: '默认 1.5 小时' },
  { type: 'hotel', duration_minutes: 30, desc: '默认 30 分钟' },
]

const posDays = ref<PosDay[]>([])

function openAdd() {
  showAddMenu.value = true
}

function chooseReal() {
  showAddMenu.value = false
  pickedPoi.value = null
  showPoiPicker.value = true
}

function choosePlaceholder() {
  showAddMenu.value = false
  showPlaceholder.value = true
}

function onPickedPoi(p: Poi) {
  pickedPoi.value = p
  posDays.value = [{ day_no: props.day.day_no, nodes: props.day.nodes.map((n) => ({ id: n.id, name: n.name })) }]
  showPosition.value = true
}

function onPosition(choice: { dayNo: number; afterNodeId: number | null; label: string }) {
  const p = pickedPoi.value
  if (!p) return
  const dur = p.poi_type === 'hotel' ? 30 : p.poi_type === 'restaurant' ? 90 : 180
  run(() => timelineApi.addNode(props.tripId, choice.dayNo, {
    node_type: p.poi_type,
    name: p.name,
    duration_minutes: dur,
    poi_id: p.id,
    after_node_id: choice.afterNodeId,
  }), `已插入到 ${choice.label}`)
}

function addPlaceholder(type: NodeType, duration: number) {
  showPlaceholder.value = false
  run(() => timelineApi.addNode(props.tripId, props.day.day_no, {
    node_type: type,
    name: `${NODE_TYPE_NAMES[type]}（占位）`,
    duration_minutes: duration,
  }), '已添加占位节点')
}

function edgeOf(node: ItineraryNode): ItineraryEdge | null {
  return props.day.edges.find((e) => e.from_node_id === node.id) ?? null
}
</script>

<template>
  <div class="tlday">
    <div class="day-head">
      <div class="day-title">
        <span class="day-no">D{{ day.day_no }}</span>
        <span v-if="day.city" class="day-city">{{ day.city }}</span>
        <span class="day-date">{{ day.date }}</span>
      </div>
      <div class="day-window">{{ day.window_start }}–{{ day.window_end }}</div>
      <div class="day-used">{{ fmtDur(day.total_used_min) }}</div>
      <div v-if="day.conflict" class="conflict-badge">超窗 {{ fmtOverflow(day.overflow_min) }}</div>
    </div>

    <div class="track">
      <template v-for="(node, i) in day.nodes" :key="node.id">
        <div class="node-card" @click="isRealPoi(node) ? openDetail(node) : openReplace(node)">
          <div class="node-icon" :style="{ color: NODE_TYPE_COLORS[node.node_type], background: NODE_TYPE_COLORS[node.node_type] + '1a' }"
            v-html="nodeIcons[node.node_type] || ''"></div>
          <div class="node-main">
            <div class="node-name-row">
              <span class="node-name">{{ node.name }}</span>
              <span class="node-type">{{ NODE_TYPE_NAMES[node.node_type] }}</span>
              <span v-if="isRealPoi(node)" class="poi-badge">真实</span>
              <span v-else-if="isAiPoi(node)" class="ai-badge">AI推荐</span>
              <span v-else class="ph-badge">占位</span>
            </div>
            <div class="node-time">
              {{ node.start_time }}–{{ node.end_time }}
              <span class="node-dur">{{ fmtDur(node.duration_minutes) }}</span>
            </div>
            <div v-if="isRealPoi(node)" class="poi-meta">
              <span v-if="node.poi!.open_hours">营业 {{ node.poi!.open_hours }}</span>
              <span v-if="node.poi!.ticket_price">{{ node.poi!.ticket_price }}</span>
              <span v-if="node.poi!.rating">评分 {{ node.poi!.rating }}</span>
            </div>
            <div v-else-if="isAiPoi(node)" class="ai-tip">点击可替换为高德真实地点</div>
            <div v-else class="ph-tip">点击替换为真实地点</div>
            <div class="node-ops" @click.stop>
              <button class="op" title="减 30 分钟" @click="adjust(node, -30)">−30m</button>
              <button class="op" title="加 30 分钟" @click="adjust(node, 30)">+30m</button>
              <button class="op" :disabled="i === 0" title="上移" @click="move(node, 'up')">↑</button>
              <button class="op" :disabled="i === day.nodes.length - 1" title="下移" @click="move(node, 'down')">↓</button>
              <button class="op op-del" title="删除" @click="remove(node)">删</button>
            </div>
          </div>
        </div>

        <div v-if="i < day.nodes.length - 1" class="edge-row">
          <div class="vline">
            <span class="varrow"></span>
          </div>
          <div v-if="edgeOf(node)" class="edge-info" @click="openTransport(edgeOf(node)!)">
            <span class="edge-ico" v-html="transportIcons[edgeOf(node)!.transport] || ''"></span>
            <span class="edge-mode">{{ TRANSPORT_NAMES[edgeOf(node)!.transport] }}</span>
            <span class="edge-dur">{{ fmtDur(edgeOf(node)!.duration_minutes) }}</span>
            <span class="edge-tap">切换</span>
          </div>
        </div>
      </template>
    </div>

    <button class="add-btn" @click="openAdd">＋ 添加节点</button>

    <!-- 添加：真实地点 / 占位 -->
    <van-popup v-model:show="showAddMenu" position="bottom" round>
      <div class="sheet">
        <div class="sheet-title">添加节点</div>
        <div class="add-menu">
          <div class="add-menu-item" @click="chooseReal">
            <span class="am-ico" v-html="transportIcons['walk']"></span>
            <span class="am-main">
              <span class="am-name">搜索真实地点</span>
              <span class="am-desc">从地点库搜索酒店/景点/餐厅，插入指定位置</span>
            </span>
          </div>
          <div class="add-menu-item" @click="choosePlaceholder">
            <span class="am-ico" v-html="nodeIcons['attraction']"></span>
            <span class="am-main">
              <span class="am-name">添加占位节点</span>
              <span class="am-desc">先占位（酒店/景点/餐厅统称），之后细化成真实地点</span>
            </span>
          </div>
        </div>
      </div>
    </van-popup>

    <!-- 占位类型 -->
    <van-popup v-model:show="showPlaceholder" position="bottom" round>
      <div class="sheet">
        <div class="sheet-title">选择占位类型（追加到当天末尾）</div>
        <div class="add-grid">
          <div v-for="p in ADD_PRESETS" :key="p.type" class="add-item"
            :style="{ color: NODE_TYPE_COLORS[p.type] }" @click="addPlaceholder(p.type, p.duration_minutes)">
            <span class="add-ico" v-html="nodeIcons[p.type]"></span>
            <span class="add-name">{{ NODE_TYPE_NAMES[p.type] }}</span>
            <span class="add-desc">{{ p.desc }}</span>
          </div>
        </div>
      </div>
    </van-popup>

    <!-- 替换为真实地点 -->
    <PoiPicker v-model:show="showReplace" :city="destCity" :type="replaceTarget?.node_type ?? null"
      :title="`替换「${replaceTarget?.name ?? ''}」为真实地点`" :initial-keyword="replaceTarget?.name ?? ''"
      @select="onReplacePoi" />

    <!-- 添加：搜索真实地点 -->
    <PoiPicker v-model:show="showPoiPicker" :city="destCity" :type="null" :title="'添加真实地点'" @select="onPickedPoi" />

    <!-- 插入位置 -->
    <PositionPicker v-model:show="showPosition" :days="posDays" :default-day-no="day.day_no"
      :title="`插入「${pickedPoi?.name ?? ''}」到位置`" @select="onPosition" />

    <!-- 交通选择 -->
    <van-popup v-model:show="showTransport" position="bottom" round>
      <div class="sheet">
        <div class="sheet-title">选择交通方式</div>
        <div class="t-grid">
          <div v-for="t in TRANSPORTS" :key="t" class="t-item"
            :class="{ active: activeEdge?.transport === t }" @click="pickTransport(t)">
            <span class="t-ico" v-html="transportIcons[t]"></span>
            <span class="t-name">{{ TRANSPORT_NAMES[t] }}</span>
          </div>
        </div>
      </div>
    </van-popup>

    <!-- 真实地点详情 -->
    <van-popup v-model:show="showDetail" position="bottom" round>
      <div class="sheet" v-if="detailNode?.poi">
        <div class="dt-name">{{ detailNode.name }}</div>
        <div class="dt-type">{{ NODE_TYPE_NAMES[detailNode.poi.poi_type] }}</div>
        <div class="dt-rows">
          <div v-if="detailNode.poi.address" class="dt-row"><span class="dt-k">地址</span><span class="dt-v">{{ detailNode.poi.address }}</span></div>
          <div v-if="detailNode.poi.open_hours" class="dt-row"><span class="dt-k">营业时间</span><span class="dt-v">{{ detailNode.poi.open_hours }}</span></div>
          <div v-if="detailNode.poi.ticket_price" class="dt-row"><span class="dt-k">票价</span><span class="dt-v">{{ detailNode.poi.ticket_price }}</span></div>
          <div v-if="detailNode.poi.rating" class="dt-row"><span class="dt-k">评分</span><span class="dt-v">{{ detailNode.poi.rating }} / 5</span></div>
          <div class="dt-row"><span class="dt-k">行程时段</span><span class="dt-v">{{ detailNode.start_time }}–{{ detailNode.end_time }}（{{ fmtDur(detailNode.duration_minutes) }}）</span></div>
        </div>
        <van-button type="primary" round block @click="showDetail = false; openReplace(detailNode!)">替换为其他地点</van-button>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.tlday {
  background: #fff;
  border: 1px solid var(--tc-line);
  border-radius: 14px;
  padding: 12px 14px 14px;
  margin-bottom: 14px;
}

/* 头部 */
.day-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--tc-line);
}
.day-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.day-no {
  font-size: 16px;
  font-weight: 800;
  color: var(--tc-teal-deep);
}
.day-city {
  font-size: 11px;
  font-weight: 700;
  color: var(--tc-orange);
  background: #fceedb;
  border-radius: 7px;
  padding: 1px 8px;
  flex: none;
}
.day-date {
  font-size: 12.5px;
  color: var(--tc-ink-2);
}
.day-window {
  font-size: 12px;
  color: var(--tc-ink-3);
  background: var(--tc-bg);
  border-radius: 8px;
  padding: 2px 8px;
}
.day-used {
  font-size: 12px;
  font-weight: 700;
  color: var(--tc-teal-deep);
}
.conflict-badge {
  font-size: 11px;
  font-weight: 700;
  color: #c94f4a;
  background: #fdf0ef;
  border-radius: 999px;
  padding: 2px 9px;
  margin-left: auto;
}

/* 节点 */
.node-card {
  display: flex;
  gap: 10px;
  padding: 12px 0 4px;
  cursor: pointer;
}
.node-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.node-icon :deep(svg) {
  width: 22px;
  height: 22px;
}
.node-main {
  flex: 1;
  min-width: 0;
}
.node-name-row {
  display: flex;
  align-items: center;
  gap: 7px;
}
.node-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--tc-ink);
}
.node-type {
  font-size: 10.5px;
  color: var(--tc-ink-3);
  border: 1px solid var(--tc-line);
  border-radius: 6px;
  padding: 0 6px;
}
.poi-badge {
  font-size: 10px;
  color: var(--tc-teal-deep);
  background: var(--tc-teal-soft);
  border-radius: 6px;
  padding: 0 6px;
}
.ph-badge {
  font-size: 10px;
  color: var(--tc-ink-3);
  background: var(--tc-bg);
  border-radius: 6px;
  padding: 0 6px;
}
.ai-badge {
  font-size: 10px;
  color: #722ed1;
  background: #f9f0ff;
  border-radius: 6px;
  padding: 0 6px;
}
.node-time {
  margin-top: 3px;
  font-size: 12px;
  color: var(--tc-ink-2);
}
.node-dur {
  margin-left: 8px;
  font-weight: 700;
  color: var(--tc-teal-deep);
}
.poi-meta {
  margin-top: 3px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 11px;
  color: var(--tc-ink-3);
}
.ph-tip {
  margin-top: 3px;
  font-size: 11px;
  color: var(--tc-orange);
}
.ai-tip {
  margin-top: 3px;
  font-size: 11px;
  color: #722ed1;
}
.node-ops {
  margin-top: 7px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.op {
  min-width: 34px;
  height: 28px;
  border: 1px solid var(--tc-line);
  background: #fbfdfc;
  color: var(--tc-ink-2);
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
  padding: 0 7px;
}
.op:disabled {
  opacity: 0.35;
}
.op-del {
  color: #c94f4a;
  border-color: #f0cfcd;
}

/* 边 */
.edge-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 2px 0 2px 20px;
}
.vline {
  position: relative;
  width: 2px;
  height: 26px;
  background: repeating-linear-gradient(180deg, var(--tc-teal) 0 4px, transparent 4px 7px);
  flex: none;
}
.varrow {
  position: absolute;
  left: 50%;
  bottom: -1px;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 7px solid var(--tc-teal);
}
.edge-info {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--tc-teal-soft);
  border-radius: 999px;
  padding: 4px 12px 4px 9px;
  font-size: 12px;
  color: var(--tc-teal-deep);
  cursor: pointer;
}
.edge-ico :deep(svg) {
  width: 15px;
  height: 15px;
}
.edge-mode {
  font-weight: 700;
}
.edge-dur {
  color: var(--tc-ink-2);
}
.edge-tap {
  font-size: 11px;
  color: var(--tc-teal);
  border: 1px solid var(--tc-teal);
  border-radius: 999px;
  padding: 0 7px;
  opacity: 0.85;
}

/* 添加 */
.add-btn {
  width: 100%;
  margin-top: 10px;
  border: 1.5px dashed var(--tc-teal);
  background: transparent;
  color: var(--tc-teal);
  border-radius: 12px;
  padding: 10px 0;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
}

/* 弹层 */
.sheet {
  padding: 16px 18px calc(20px + env(safe-area-inset-bottom));
}
.sheet-title {
  font-size: 15px;
  font-weight: 700;
  text-align: center;
  margin-bottom: 14px;
}
.add-menu {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.add-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 14px;
  border: 1px solid var(--tc-line);
  border-radius: 12px;
  background: #fbfdfc;
  cursor: pointer;
}
.am-ico {
  color: var(--tc-teal);
  display: flex;
}
.am-ico :deep(svg) {
  width: 24px;
  height: 24px;
}
.am-main {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.am-name {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--tc-ink);
}
.am-desc {
  font-size: 11.5px;
  color: var(--tc-ink-3);
}
.t-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.t-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 12px 0;
  border: 1px solid var(--tc-line);
  border-radius: 12px;
  background: #fbfdfc;
  color: var(--tc-ink-2);
  font-size: 12px;
  cursor: pointer;
}
.t-item.active {
  border-color: var(--tc-teal);
  background: var(--tc-teal-soft);
  color: var(--tc-teal-deep);
  font-weight: 700;
}
.t-ico :deep(svg) {
  width: 22px;
  height: 22px;
}
.add-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.add-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 14px 0;
  border: 1px solid var(--tc-line);
  border-radius: 12px;
  background: #fbfdfc;
  cursor: pointer;
}
.add-ico :deep(svg) {
  width: 26px;
  height: 26px;
}
.add-name {
  font-size: 13.5px;
  font-weight: 700;
}
.add-desc {
  font-size: 11px;
  color: var(--tc-ink-3);
}

/* 详情 */
.dt-name {
  font-size: 17px;
  font-weight: 800;
  text-align: center;
}
.dt-type {
  text-align: center;
  font-size: 12px;
  color: var(--tc-ink-3);
  margin: 4px 0 14px;
}
.dt-rows {
  margin-bottom: 14px;
}
.dt-row {
  display: flex;
  gap: 12px;
  padding: 8px 2px;
  font-size: 13px;
  border-bottom: 1px dashed var(--tc-line);
}
.dt-k {
  flex: none;
  width: 64px;
  color: var(--tc-ink-3);
}
.dt-v {
  color: var(--tc-ink);
  word-break: break-all;
}
</style>
