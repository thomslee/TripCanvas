<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { settingsApi, type AppSettings } from '../api'

const router = useRouter()
const loading = ref(true)
const saving = ref(false)

// 表单：api_key 类字段单独跟踪是否已修改（脱敏值不回传）
const form = reactive({
  llm_base_url: '',
  llm_api_key: '',       // 用户输入的新 key，空表示不修改
  llm_model: '',
  amap_key: '',          // 同上
  weather_provider: 'open-meteo',
})
const masked = reactive({
  llm_api_key: false,    // 后端返回了脱敏值（说明已配置）
  amap_key: false,
})

async function load() {
  loading.value = true
  try {
    const { data } = await settingsApi.get()
    form.llm_base_url = data.llm_base_url
    form.llm_model = data.llm_model
    form.weather_provider = data.weather_provider
    // 脱敏字段：有值则标记已配置，输入框留空（placeholder 提示）
    masked.llm_api_key = data.llm_api_key === '••••••••'
    masked.amap_key = data.amap_key === '••••••••'
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    loading.value = false
  }
}

async function onSave() {
  if (saving.value) return
  saving.value = true
  try {
    const payload: Partial<AppSettings> = {
      llm_base_url: form.llm_base_url.trim(),
      llm_model: form.llm_model.trim(),
      weather_provider: form.weather_provider,
    }
    // 只有用户输入了新 key 才传，空字符串表示清除（用户主动清空）
    if (form.llm_api_key) payload.llm_api_key = form.llm_api_key.trim()
    else if (!masked.llm_api_key) payload.llm_api_key = ''
    if (form.amap_key) payload.amap_key = form.amap_key.trim()
    else if (!masked.amap_key) payload.amap_key = ''

    const { data } = await settingsApi.update(payload)
    // 更新脱敏状态
    masked.llm_api_key = data.llm_api_key === '••••••••'
    masked.amap_key = data.amap_key === '••••••••'
    form.llm_api_key = ''
    form.amap_key = ''
    showToast('设置已保存')
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="tc-page">
    <van-nav-bar title="设置" left-arrow @click-left="router.back()" fixed placeholder />

    <van-loading v-if="loading" style="padding: 60px 0" color="#0e7c7e" vertical>加载中…</van-loading>

    <template v-else>
      <div class="section-title">大模型 API</div>
      <div class="tc-card">
        <van-field v-model="form.llm_base_url" label="API 地址" placeholder="如 https://api.openai.com/v1" />
        <van-field v-model="form.llm_api_key" label="API Key" type="password"
          :placeholder="masked.llm_api_key ? '已配置，留空不修改' : '输入 API Key'" />
        <van-field v-model="form.llm_model" label="模型名称" placeholder="如 gpt-4o / doubao-pro" />
      </div>

      <div class="section-title">高德地图</div>
      <div class="tc-card">
        <van-field v-model="form.amap_key" label="API Key" type="password"
          :placeholder="masked.amap_key ? '已配置，留空不修改' : '输入高德 Web 服务 Key'" />
        <div class="field-hint">用于真实 POI 搜索、地点详情与路线规划；当前使用内置示例数据</div>
      </div>

      <div class="section-title">天气服务</div>
      <div class="tc-card">
        <van-field name="weather_provider" label="服务提供商">
          <template #input>
            <span class="readonly-val">{{ form.weather_provider }}</span>
          </template>
        </van-field>
        <div class="field-hint">当前使用 open-meteo（免费、无需 Key），后续可扩展其他服务商</div>
      </div>

      <div class="save-area">
        <van-button type="primary" block round :loading="saving" @click="onSave">保存设置</van-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.section-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--tc-ink-3);
  margin: 16px 16px 6px;
  letter-spacing: 0.5px;
}
.field-hint {
  font-size: 11px;
  color: var(--tc-ink-3);
  padding: 0 16px 10px;
  line-height: 1.5;
}
.readonly-val {
  font-size: 14px;
  color: var(--tc-ink-2);
}
.save-area {
  padding: 24px 16px calc(24px + env(safe-area-inset-bottom));
}
</style>
