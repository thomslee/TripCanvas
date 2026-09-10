<script setup lang="ts">
import { computed, ref, watch } from 'vue'

export interface PosDay {
  day_no: number
  date?: string
  nodes: { id: number; name: string }[]
}

export interface PosChoice {
  dayNo: number
  afterNodeId: number | null // -1 = 最前面；>0 = 某节点之后；null = 追加末尾
  label: string
}

const props = defineProps<{
  show: boolean
  days: PosDay[]
  defaultDayNo?: number
  title?: string
}>()
const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'select', choice: PosChoice): void
}>()

const curDay = ref(0)

watch(
  () => props.show,
  (v) => {
    if (v) {
      curDay.value = props.defaultDayNo ?? props.days[0]?.day_no ?? 0
    }
  },
)

const cur = computed(() => props.days.find((d) => d.day_no === curDay.value) ?? null)

function pick(dayNo: number, afterNodeId: number | null, label: string) {
  emit('select', { dayNo, afterNodeId, label })
  emit('update:show', false)
}

function close() {
  emit('update:show', false)
}
</script>

<template>
  <van-popup :show="show" position="bottom" round style="max-height: 70%" @update:show="(v: boolean) => emit('update:show', v)">
    <div class="pp">
      <div class="pp-head">
        <span class="pp-title">{{ title || '插入位置' }}</span>
        <span class="pp-close" @click="close">关闭</span>
      </div>
      <div class="pp-days">
        <span v-for="d in days" :key="d.day_no" class="day-chip"
          :class="{ on: curDay === d.day_no }" @click="curDay = d.day_no">
          D{{ d.day_no }}
        </span>
      </div>
      <div v-if="cur" class="pp-list">
        <div class="pos-row" @click="pick(cur.day_no, -1, `D${cur.day_no} 最前面`)">
          <span class="pos-ico">⤒</span>
          <span class="pos-name">D{{ cur.day_no }} · 最前面</span>
        </div>
        <div v-for="(n, i) in cur.nodes" :key="n.id" class="pos-row"
          @click="pick(cur.day_no, n.id, `D${cur.day_no} ${n.name}之后`)">
          <span class="pos-ico">↓</span>
          <span class="pos-name">D{{ cur.day_no }} · {{ n.name }}<span v-if="i < cur.nodes.length - 1">之后</span><span v-else>之后（当前末尾）</span></span>
        </div>
        <div v-if="!cur.nodes.length" class="pos-empty">该天暂无节点，将插入为第一个节点</div>
      </div>
    </div>
  </van-popup>
</template>

<style scoped>
.pp {
  padding: 16px 16px calc(20px + env(safe-area-inset-bottom));
}
.pp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.pp-title {
  font-size: 15px;
  font-weight: 700;
}
.pp-close {
  font-size: 13px;
  color: var(--tc-ink-3);
  padding: 6px;
}
.pp-days {
  display: flex;
  gap: 8px;
  margin: 14px 0 10px;
  flex-wrap: wrap;
}
.day-chip {
  font-size: 12.5px;
  color: var(--tc-ink-2);
  background: var(--tc-bg);
  border: 1px solid var(--tc-line);
  border-radius: 999px;
  padding: 5px 14px;
}
.day-chip.on {
  color: #fff;
  background: var(--tc-teal);
  border-color: var(--tc-teal);
}
.pos-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 4px;
  border-bottom: 1px dashed var(--tc-line);
  cursor: pointer;
}
.pos-ico {
  color: var(--tc-teal);
  font-weight: 700;
  width: 20px;
  text-align: center;
}
.pos-name {
  font-size: 13.5px;
  color: var(--tc-ink);
}
.pos-empty {
  text-align: center;
  color: var(--tc-ink-3);
  font-size: 12.5px;
  padding: 20px 0;
}
</style>
