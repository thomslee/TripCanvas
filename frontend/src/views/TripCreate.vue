<script setup lang="ts">
import { computed, reactive, ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { tripsApi, citiesApi, poiApi, type TripCreateResult, type DayWindow } from '../api'

const router = useRouter()

const form = reactive({
  departCity: '',
  destCities: [{ city: '', days: 1 }] as { city: string; days: number }[],
  departDate: [] as string[],
  returnDate: [] as string[],
  arriveTime: [] as string[],
  departTime: [] as string[],
  departTransport: 'plane',
  arriveStation: '',
  returnTransport: 'plane',
  departStation: '',
  requirements: '',
  pace: 'relaxed',
  budget: 'mid',
  travelers: 1,
})

const transportOptions = [
  { name: '飞机', value: 'plane' },
  { name: '高铁', value: 'train' },
  { name: '自驾', value: 'car' },
]

/* ---------- 城市/站点搜索选择 ---------- */
const pickerType = ref<'departCity' | 'destCity' | 'arriveStation' | 'departStation' | null>(null)
const pickerIndex = ref(-1) // 多城市时的索引
const pickerKeyword = ref('')
const pickerResults = ref<any[]>([])
const pickerLoading = ref(false)
const showPicker = ref(false)

let citySearchTimer: any = null
async function onPickerSearch() {
  const kw = pickerKeyword.value.trim()
  pickerLoading.value = true
  try {
    if (pickerType.value === 'departCity' || pickerType.value === 'destCity') {
      const { data } = await citiesApi.search(kw)
      pickerResults.value = data
    } else {
      // 站点搜索：自驾时全国搜索任意地点，其他交通方式按城市搜索站点
      const isCar = (pickerType.value === 'arriveStation' && form.departTransport === 'car') ||
                    (pickerType.value === 'departStation' && form.returnTransport === 'car')
      if (isCar) {
        const { data } = await poiApi.searchAmap({ q: kw || '地点', city: '', limit: 20 })
        pickerResults.value = data
      } else {
        let city = ''
        if (pickerType.value === 'arriveStation') {
          city = form.destCities[0]?.city || ''
        } else if (pickerType.value === 'departStation') {
          city = form.destCities[form.destCities.length - 1]?.city || ''
        }
        const { data } = await poiApi.searchAmap({ q: kw || '机场 高铁站', city, limit: 20 })
        pickerResults.value = data.filter((p: any) => p.poi_type === 'station')
      }
    }
  } finally {
    pickerLoading.value = false
  }
}

function openPicker(type: string, index = -1) {
  pickerType.value = type as any
  pickerIndex.value = index
  pickerKeyword.value = ''
  pickerResults.value = []
  showPicker.value = true
  setTimeout(() => onPickerSearch(), 100)
}

function onPickerInput() {
  clearTimeout(citySearchTimer)
  citySearchTimer = setTimeout(onPickerSearch, 300)
}

function selectPicker(item: any) {
  if (pickerType.value === 'departCity') {
    form.departCity = item.name
  } else if (pickerType.value === 'destCity') {
    form.destCities[pickerIndex.value].city = item.name
  } else if (pickerType.value === 'arriveStation') {
    form.arriveStation = item.name
  } else if (pickerType.value === 'departStation') {
    form.departStation = item.name
  }
  showPicker.value = false
}

/* 每次进入创建页重置表单，避免保留上次填写内容 */
function resetForm() {
  form.departCity = ''
  form.destCities = [{ city: '', days: 1 }]
  form.departDate = []
  form.returnDate = []
  form.arriveTime = []
  form.departTime = []
  form.departTransport = 'plane'
  form.arriveStation = ''
  form.returnTransport = 'plane'
  form.departStation = ''
  form.requirements = ''
  form.pace = 'relaxed'
  form.budget = 'mid'
  form.travelers = 1
}
onMounted(resetForm)

const showDepartDate = ref(false)
const showReturnDate = ref(false)
const showArriveTime = ref(false)
const showDepartTime = ref(false)

const submitting = ref(false)
const result = ref<TripCreateResult | null>(null)
const showResult = ref(false)

const paceOptions = [
  { name: '宽松', value: 'relaxed' },
  { name: '适中', value: 'balanced' },
  { name: '紧凑', value: 'tight' },
]
const budgetOptions = [
  { name: '经济', value: 'economy' },
  { name: '舒适', value: 'mid' },
  { name: '高端', value: 'luxury' },
]

function jDate(a: string[]): string {
  return a.length ? a.join('-') : ''
}
function jTime(a: string[]): string | null {
  return a.length ? a.join(':') : null
}

/* ---------- 多城市：总天数 / 已分配 / 剩余 ---------- */
const totalDays = computed(() => {
  if (!form.departDate.length || !form.returnDate.length) return 0
  const [dy, dm, dd] = form.departDate.map(Number)
  const [ry, rm, rd] = form.returnDate.map(Number)
  const a = new Date(dy, dm - 1, dd).getTime()
  const b = new Date(ry, rm - 1, rd).getTime()
  if (b < a) return 0
  return Math.round((b - a) / 86400000) + 1
})
const allocatedDays = computed(() => form.destCities.reduce((s, c) => s + c.days, 0))
const remainDays = computed(() => totalDays.value - allocatedDays.value)

/* 日期变化时自动分配：单城市=全部天数；多城市=剩余天数补到最后城市 */
watch(totalDays, (td) => {
  if (!td) return
  const cities = form.destCities
  if (cities.length === 1) {
    cities[0].days = td
  } else {
    const sum = cities.reduce((s, c) => s + c.days, 0)
    if (sum < td) cities[cities.length - 1].days += td - sum
  }
})

function addCity() {
  if (form.destCities.length >= 5) {
    showToast('最多支持 5 个目的城市')
    return
  }
  form.destCities.push({ city: '', days: 1 })
  const td = totalDays.value
  if (td && remainDays.value > 0) {
    form.destCities[form.destCities.length - 1].days += remainDays.value
  }
}

function removeCity(i: number) {
  if (form.destCities.length <= 1) {
    showToast('至少保留一个目的城市')
    return
  }
  form.destCities.splice(i, 1)
  // 删除后把剩余天数归到最后一个城市
  const td = totalDays.value
  if (td && remainDays.value > 0) {
    const last = form.destCities[form.destCities.length - 1]
    last.days += remainDays.value
  }
}

async function onSubmit() {
  if (!form.departCity.trim() || !form.destCities[0].city.trim()) {
    showToast('请填写出发城市与目的城市')
    return
  }
  if (form.destCities.some((c) => !c.city.trim())) {
    showToast('目的城市名称不能为空')
    return
  }
  if (!form.departDate.length || !form.returnDate.length) {
    showToast('请选择往返日期')
    return
  }
  if (!form.arriveTime.length || !form.departTime.length) {
    showToast('请填写到达时间和返程出发时间')
    return
  }
  if (jDate(form.returnDate) < jDate(form.departDate)) {
    showToast('返程日期不能早于去程日期')
    return
  }
  if (remainDays.value !== 0) {
    showToast(remainDays.value > 0 ? `还有 ${remainDays.value} 天未分配城市` : `城市天数超出 ${-remainDays.value} 天，请调整`)
    return
  }
  submitting.value = true
  try {
    const { data } = await tripsApi.create({
      depart_city: form.departCity.trim(),
      dest_city: form.destCities[0].city.trim(),
      depart_date: jDate(form.departDate),
      arrive_time: jTime(form.arriveTime),
      return_date: jDate(form.returnDate),
      depart_time: jTime(form.departTime),
      preferences: {
        pace: form.pace, budget: form.budget, travelers: form.travelers,
        ...(form.requirements.trim() ? { requirements: form.requirements.trim() } : {}),
      },
      dest_cities: form.destCities.map((c) => ({ city: c.city.trim(), days: c.days })),
      depart_transport: form.departTransport,
      arrive_station: form.arriveStation.trim() || null,
      return_transport: form.returnTransport,
      depart_station: form.departStation.trim() || null,
    })
    result.value = data
    showResult.value = true
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    submitting.value = false
  }
}

function goDetail() {
  if (!result.value) return
  const id = result.value.trip.id
  showResult.value = false
  router.push(`/trips/${id}`)
}

function goList() {
  showResult.value = false
  router.push('/')
}

function fmtWin(w: DayWindow): string {
  return `D${w.day_no} ${w.date}  ${w.start}–${w.end}`
}
</script>

<template>
  <div class="tc-page">
    <van-nav-bar title="新建行程" left-arrow @click-left="router.back()" fixed placeholder />

    <div class="sec-label">往返信息（到达与返程时间决定行程节奏）</div>

    <div class="tc-card">
      <van-cell title="出发城市" :value="form.departCity || '请选择'" is-link
        @click="openPicker('departCity')" />

      <div class="city-label">目的城市（支持多城市连游）</div>
      <div v-for="(c, i) in form.destCities" :key="i" class="city-row">
        <van-cell :value="c.city || `请选择第${i + 1}个城市`" is-link class="city-field"
          @click="openPicker('destCity', i)" />
        <div class="city-days">
          <van-stepper v-model="c.days" min="1" :max="Math.max(totalDays, 1)" :disable-input="true" />
        </div>
        <span class="city-del" @click="removeCity(i)">删</span>
      </div>
      <div class="city-foot">
        <span class="city-add" @click="addCity">＋ 添加城市</span>
        <span v-if="totalDays" class="city-sum" :class="{ warn: remainDays !== 0 }">
          总 {{ totalDays }} 天 · 已分配 {{ allocatedDays }} 天
          <template v-if="remainDays > 0"> · 剩余 {{ remainDays }} 天</template>
          <template v-else-if="remainDays < 0"> · 超出 {{ -remainDays }} 天</template>
        </span>
      </div>

      <div class="transport-row">
        <span class="transport-label">去程交通</span>
        <van-radio-group v-model="form.departTransport" direction="horizontal">
          <van-radio v-for="o in transportOptions" :key="o.value" :name="o.value">{{ o.name }}</van-radio>
        </van-radio-group>
      </div>
      <van-cell title="到达站点" :value="form.arriveStation || (form.departTransport === 'car' ? '请选择目的地（选填）' : '请选择（选填）')" is-link
        @click="openPicker('arriveStation')" />
      <van-cell title="到达日期" is-link :value="form.departDate.length ? jDate(form.departDate) : ''"
        placeholder="必填" @click="showDepartDate = true" />
      <van-cell title="到达时间" is-link
        :value="form.arriveTime.length ? jTime(form.arriveTime)! : ''" placeholder="必填"
        @click="showArriveTime = true" />

      <div class="transport-row">
        <span class="transport-label">返程交通</span>
        <van-radio-group v-model="form.returnTransport" direction="horizontal">
          <van-radio v-for="o in transportOptions" :key="o.value" :name="o.value">{{ o.name }}</van-radio>
        </van-radio-group>
      </div>
      <van-cell title="出发站点" :value="form.departStation || (form.returnTransport === 'car' ? '请选择出发地（选填）' : '请选择（选填）')" is-link
        @click="openPicker('departStation')" />
      <van-cell title="出发日期" is-link :value="form.returnDate.length ? jDate(form.returnDate) : ''"
        placeholder="必填" @click="showReturnDate = true" />
      <van-cell title="出发时间" is-link
        :value="form.departTime.length ? jTime(form.departTime)! : ''" placeholder="必填"
        @click="showDepartTime = true" />
    </div>

    <div class="sec-label">偏好（用于后续 AI 推荐）</div>
    <div class="tc-card">
      <div class="pref-row">
        <span class="pref-label">节奏</span>
        <van-radio-group v-model="form.pace" direction="horizontal">
          <van-radio v-for="o in paceOptions" :key="o.value" :name="o.value">{{ o.name }}</van-radio>
        </van-radio-group>
      </div>
      <div class="pref-row">
        <span class="pref-label">预算</span>
        <van-radio-group v-model="form.budget" direction="horizontal">
          <van-radio v-for="o in budgetOptions" :key="o.value" :name="o.value">{{ o.name }}</van-radio>
        </van-radio-group>
      </div>
      <div class="pref-row">
        <span class="pref-label">人数</span>
        <van-stepper v-model="form.travelers" min="1" max="20" />
      </div>
      <div class="pref-row pref-col">
        <span class="pref-label">旅游要求</span>
        <van-field v-model="form.requirements" type="textarea" rows="2" autosize
          placeholder="选填，如：住在古城附近、喜欢安静的客栈、带老人小孩、必去某景点等" maxlength="200" />
      </div>
    </div>

    <div style="padding: 8px 0 20px">
      <van-button type="primary" block round :loading="submitting" @click="onSubmit">
        生成行程
      </van-button>
    </div>

    <!-- 日期选择 -->
    <van-popup v-model:show="showDepartDate" position="bottom" round>
      <van-date-picker v-model="form.departDate" title="选择到达日期" :min-date="new Date()"
        @confirm="showDepartDate = false" @cancel="showDepartDate = false" />
    </van-popup>
    <van-popup v-model:show="showReturnDate" position="bottom" round>
      <van-date-picker v-model="form.returnDate" title="选择出发日期" :min-date="new Date()"
        @confirm="showReturnDate = false" @cancel="showReturnDate = false" />
    </van-popup>

    <!-- 时间选择 -->
    <van-popup v-model:show="showArriveTime" position="bottom" round>
      <van-time-picker v-model="form.arriveTime" title="到达时间" @confirm="showArriveTime = false"
        @cancel="showArriveTime = false" />
    </van-popup>
    <van-popup v-model:show="showDepartTime" position="bottom" round>
      <van-time-picker v-model="form.departTime" title="起飞时间" @confirm="showDepartTime = false"
        @cancel="showDepartTime = false" />
    </van-popup>

    <!-- 城市/站点搜索选择 -->
    <van-popup v-model:show="showPicker" position="bottom" round :style="{ height: '70%' }">
      <div class="picker-header">
        <div class="picker-title">
          {{ pickerType === 'departCity' ? '选择出发城市' : pickerType === 'destCity' ? '选择目的城市' : pickerType === 'arriveStation' ? '选择到达站点' : '选择出发站点' }}
        </div>
        <van-icon name="cross" @click="showPicker = false" />
      </div>
      <van-search v-model="pickerKeyword" placeholder="输入关键词搜索" @search="onPickerSearch"
        @update:model-value="onPickerInput" :loading="pickerLoading" />
      <div class="picker-list">
        <div v-if="pickerResults.length === 0 && !pickerLoading" class="picker-empty">
          未找到相关结果
        </div>
        <van-cell v-for="(item, i) in pickerResults" :key="i"
          :title="item.name"
          :label="item.province ? item.province + ' · ' + item.pinyin : item.address"
          is-link @click="selectPicker(item)" />
      </div>
    </van-popup>

    <!-- 生成结果 -->
    <van-popup v-model:show="showResult" position="bottom" round style="max-height: 70%">
      <div style="padding: 18px 18px 24px">
        <div style="font-size: 17px; font-weight: 700; display: flex; align-items: center; gap: 8px">
          <span>行程已生成</span>
          <span style="font-size: 12px; color: var(--tc-teal-deep); background: var(--tc-teal-soft); padding: 2px 10px; border-radius: 999px">
            {{ result?.trip.title }}
          </span>
        </div>
        <div style="font-size: 13px; color: var(--tc-ink-2); margin-top: 8px">
          共 {{ result?.trip.total_days }} 天，每天可用游玩时间：
        </div>
        <div style="margin-top: 12px; display: flex; flex-direction: column; gap: 8px">
          <div v-for="w in result?.windows" :key="w.day_no" class="win-row">
            <span class="win-d">{{ fmtWin(w) }}</span>
            <span class="win-note">{{ w.note }}</span>
          </div>
        </div>
        <div v-if="result?.messages?.length" style="margin-top: 12px">
          <div v-for="(m, i) in result.messages" :key="i" class="win-msg">{{ m }}</div>
        </div>
        <div style="display: flex; gap: 10px; margin-top: 18px">
          <van-button round block style="flex: 1" @click="goList">回列表</van-button>
          <van-button type="primary" round block style="flex: 2" @click="goDetail">进入行程</van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.sec-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--tc-teal-deep);
  letter-spacing: 1px;
  margin: 14px 2px 8px;
}
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.row2 :deep(.van-field) {
  padding: 8px 10px;
  background: #fbfdfc;
  border: 1px solid var(--tc-line);
  border-radius: 10px;
}
.city-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--tc-ink-2);
  margin: 12px 2px 6px;
}
.city-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.city-field {
  flex: 1;
  min-width: 0;
  background: #fbfdfc;
  border: 1px solid var(--tc-line);
  border-radius: 10px;
  padding: 4px 0;
}
.city-days {
  flex: none;
}
.city-del {
  flex: none;
  font-size: 12px;
  color: #c94f4a;
  border: 1px solid #f0cfcd;
  border-radius: 8px;
  padding: 4px 10px;
  cursor: pointer;
}
.city-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin: 2px 2px 10px;
  flex-wrap: wrap;
}
.city-add {
  font-size: 13px;
  font-weight: 600;
  color: var(--tc-teal);
  cursor: pointer;
}
.city-sum {
  font-size: 11.5px;
  color: var(--tc-ink-3);
}
.city-sum.warn {
  color: var(--tc-orange);
}
.pref-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
}
.pref-row + .pref-row {
  border-top: 1px dashed var(--tc-line);
}
.pref-label {
  font-size: 13.5px;
  color: var(--tc-ink-2);
}
.pref-col {
  flex-direction: column;
  align-items: stretch;
  gap: 6px;
}
.transport-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-top: 1px solid var(--tc-line);
}
.transport-label {
  font-size: 13.5px;
  color: var(--tc-ink-2);
  flex: none;
}
.win-row {
  background: #fbfdfc;
  border: 1px solid var(--tc-line);
  border-radius: 10px;
  padding: 9px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.win-d {
  font-size: 13px;
  font-weight: 600;
}
.win-note {
  font-size: 11.5px;
  color: var(--tc-ink-3);
  text-align: right;
}
.win-msg {
  font-size: 12px;
  color: var(--tc-orange);
  background: var(--tc-orange-soft, #fceedb);
  border-radius: 8px;
  padding: 6px 10px;
  margin-bottom: 6px;
}
.picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px 8px;
}
.picker-title {
  font-size: 16px;
  font-weight: 700;
}
.picker-list {
  max-height: calc(70vh - 120px);
  overflow-y: auto;
}
.picker-empty {
  padding: 40px;
  text-align: center;
  color: #999;
  font-size: 14px;
}
</style>
