<script setup lang="ts">
import { ref, watch } from 'vue'
import { poiApi, type Poi, type NodeType } from '../api'

const props = defineProps<{
  show: boolean
  city?: string | null
  type?: NodeType | null
  title?: string
  initialKeyword?: string
}>()
const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'select', poi: Poi): void
}>()

const keyword = ref('')
const typeFilter = ref<NodeType | null>(props.type ?? null)
const results = ref<Poi[]>([])
const loading = ref(false)
const searched = ref(false)

const TYPES: { label: string; value: NodeType | null }[] = [
  { label: '全部', value: null },
  { label: '酒店', value: 'hotel' },
  { label: '景点', value: 'attraction' },
  { label: '餐厅', value: 'restaurant' },
  { label: '交通', value: 'station' },
]

watch(
  () => props.show,
  (v) => {
    if (v) {
      typeFilter.value = props.type ?? null
      keyword.value = props.initialKeyword ?? ''
      results.value = []
      searched.value = false
      doSearch()
    }
  },
)

async function doSearch() {
  loading.value = true
  try {
    const kw = keyword.value.trim()
    // 同时搜索内置库和高德（有关键词时才搜高德，避免无关键词返回过多）
    const tasks: Promise<any>[] = [
      poiApi.search({
        city: props.city ?? undefined,
        q: kw || undefined,
        type: typeFilter.value ?? undefined,
        limit: 20,
      }),
    ]
    if (kw) {
      tasks.push(poiApi.searchAmap({
        city: props.city ?? undefined,
        q: kw,
        limit: 15,
      }).catch(() => ({ data: [] })))
    }
    const [localRes, amapRes] = await Promise.all(tasks)
    const local = localRes.data || []
    const amap = (amapRes as any)?.data || []
    // 合并去重（按 id）
    const seen = new Set<number>()
    const merged: Poi[] = []
    for (const p of [...amap, ...local]) {
      if (!seen.has(p.id)) {
        seen.add(p.id)
        merged.push(p)
      }
    }
    // 按类型过滤
    results.value = typeFilter.value
      ? merged.filter((p) => p.poi_type === typeFilter.value)
      : merged
    searched.value = true
  } catch (e) {
    results.value = []
    searched.value = true
    console.error(e)
  } finally {
    loading.value = false
  }
}

function pick(p: Poi) {
  emit('select', p)
  emit('update:show', false)
}

function close() {
  emit('update:show', false)
}
</script>

<template>
  <van-popup :show="show" position="bottom" round style="height: 72%" @update:show="(v: boolean) => emit('update:show', v)">
    <div class="pk">
      <div class="pk-head">
        <span class="pk-title">{{ title || '选择真实地点' }}</span>
        <span class="pk-close" @click="close">关闭</span>
      </div>
      <div class="pk-search">
        <van-search v-model="keyword" placeholder="输入名称搜索（如：洱海）" shape="round"
          show-action @search="doSearch" @clear="doSearch">
          <template #action>
            <div class="pk-go" @click="doSearch">搜索</div>
          </template>
        </van-search>
        <div class="pk-chips">
          <span v-for="t in TYPES" :key="t.label" class="chip"
            :class="{ on: typeFilter === t.value }" @click="typeFilter = t.value; doSearch()">
            {{ t.label }}
          </span>
        </div>
      </div>
      <div class="pk-list">
        <van-loading v-if="loading" style="padding: 30px 0" vertical>搜索中…</van-loading>
        <div v-else-if="searched && !results.length" class="pk-empty">
          未找到匹配地点，试试换个关键词或城市。
        </div>
        <div v-for="p in results" :key="p.id" class="pk-item" @click="pick(p)">
          <div class="pk-main">
            <div class="pk-name">
              {{ p.name }}
              <span v-if="p.source === 'gaode'" class="pk-src gaode">高德</span>
              <span v-else-if="p.source === 'seed'" class="pk-src">示例</span>
              <span v-else-if="p.source === 'ai'" class="pk-src ai">AI</span>
            </div>
            <div class="pk-meta">
              <span v-if="p.open_hours">营业 {{ p.open_hours }}</span>
              <span v-if="p.ticket_price">{{ p.ticket_price }}</span>
              <span v-if="p.rating">评分 {{ p.rating }}</span>
            </div>
            <div v-if="p.address" class="pk-addr">{{ p.address }}</div>
          </div>
        </div>
      </div>
    </div>
  </van-popup>
</template>

<style scoped>
.pk {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.pk-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px 4px;
}
.pk-title {
  font-size: 15px;
  font-weight: 700;
}
.pk-close {
  font-size: 13px;
  color: var(--tc-ink-3);
  padding: 6px;
}
.pk-search {
  padding: 0 10px;
}
.pk-chips {
  display: flex;
  gap: 8px;
  padding: 6px 6px 10px;
}
.pk-go {
  font-size: 14px;
  font-weight: 700;
  color: var(--tc-teal-deep);
  padding: 0 4px 0 10px;
}
.chip {
  font-size: 12px;
  color: var(--tc-ink-2);
  background: var(--tc-bg);
  border: 1px solid var(--tc-line);
  border-radius: 999px;
  padding: 4px 13px;
}
.chip.on {
  color: #fff;
  background: var(--tc-teal);
  border-color: var(--tc-teal);
}
.pk-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px 20px;
}
.pk-empty {
  text-align: center;
  color: var(--tc-ink-3);
  font-size: 12.5px;
  padding: 30px 10px;
  line-height: 1.7;
}
.pk-item {
  display: flex;
  padding: 11px 4px;
  border-bottom: 1px dashed var(--tc-line);
}
.pk-main {
  min-width: 0;
}
.pk-name {
  font-size: 14.5px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}
.pk-src {
  font-size: 10px;
  color: var(--tc-orange);
  border: 1px solid var(--tc-orange);
  border-radius: 4px;
  padding: 0 4px;
}
.pk-src.gaode {
  color: #1677ff;
  border-color: #1677ff;
}
.pk-src.ai {
  color: #722ed1;
  border-color: #722ed1;
}
.pk-meta {
  margin-top: 3px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11.5px;
  color: var(--tc-ink-3);
}
.pk-addr {
  margin-top: 2px;
  font-size: 11.5px;
  color: var(--tc-ink-3);
}
</style>
