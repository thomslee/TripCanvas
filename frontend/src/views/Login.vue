<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const nickname = ref('')
const submitting = ref(false)

async function onSubmit() {
  if (!username.value.trim() || !password.value) {
    showToast('请输入用户名和密码')
    return
  }
  submitting.value = true
  try {
    if (mode.value === 'login') {
      await userStore.login(username.value.trim(), password.value)
      showToast('登录成功')
    } else {
      await userStore.register(username.value.trim(), password.value, nickname.value.trim() || undefined)
      showToast('注册成功')
    }
    router.push('/')
  } catch (e: any) {
    showToast(e.message || '操作失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-logo">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#0e7c7e" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
          <circle cx="12" cy="10" r="3"/>
        </svg>
        <h1>途迹 TripCanvas</h1>
        <p>智能旅游行程规划</p>
      </div>

      <div class="login-tabs">
        <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
        <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
      </div>

      <form @submit.prevent="onSubmit" class="login-form">
        <div class="form-item">
          <label>用户名</label>
          <input v-model="username" type="text" placeholder="请输入用户名" autocomplete="username" />
        </div>
        <div v-if="mode === 'register'" class="form-item">
          <label>昵称（可选）</label>
          <input v-model="nickname" type="text" placeholder="显示名称" />
        </div>
        <div class="form-item">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="请输入密码" autocomplete="current-password" />
        </div>
        <button type="submit" class="submit-btn" :disabled="submitting">
          {{ submitting ? '处理中…' : (mode === 'login' ? '登 录' : '注 册') }}
        </button>
      </form>

      <p class="login-hint">
        <template v-if="mode === 'login'">还没有账号？<span @click="mode = 'register'">立即注册</span></template>
        <template v-else>已有账号？<span @click="mode = 'login'">去登录</span></template>
      </p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(160deg, #e8f5f3 0%, #f0f7f4 50%, #f7f9f6 100%);
  padding: 20px;
}
.login-card {
  width: 100%;
  max-width: 380px;
  background: #fff;
  border-radius: 16px;
  padding: 32px 28px;
  box-shadow: 0 8px 32px rgba(14, 124, 126, 0.1);
}
.login-logo {
  text-align: center;
  margin-bottom: 24px;
}
.login-logo h1 {
  font-size: 22px;
  font-weight: 700;
  color: #0e7c7e;
  margin: 8px 0 4px;
}
.login-logo p {
  font-size: 13px;
  color: #8a9a97;
  margin: 0;
}
.login-tabs {
  display: flex;
  background: #f0f4f3;
  border-radius: 10px;
  padding: 4px;
  margin-bottom: 20px;
}
.login-tabs button {
  flex: 1;
  border: none;
  background: transparent;
  padding: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #7a8a87;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.login-tabs button.active {
  background: #fff;
  color: #0e7c7e;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.form-item {
  margin-bottom: 16px;
}
.form-item label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #3a4a47;
  margin-bottom: 6px;
}
.form-item input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 14px;
  border: 1px solid #d8e0de;
  border-radius: 10px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}
.form-item input:focus {
  border-color: #0e7c7e;
}
.submit-btn {
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #0e7c7e, #12a5a8);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.2s;
}
.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.login-hint {
  text-align: center;
  font-size: 13px;
  color: #7a8a87;
  margin: 16px 0 0;
}
.login-hint span {
  color: #0e7c7e;
  font-weight: 600;
  cursor: pointer;
}
.login-admin {
  text-align: center;
  font-size: 11px;
  color: #b0bcb9;
  margin: 8px 0 0;
}
</style>
