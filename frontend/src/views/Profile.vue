<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import { useUserStore } from '../stores/user'
import { authApi, adminApi, type AdminUser } from '../api'

const router = useRouter()
const userStore = useUserStore()

const oldPwd = ref('')
const newPwd = ref('')
const confirmPwd = ref('')
const pwdLoading = ref(false)

// 用户资料
const nickname = ref('')
const gender = ref('')
const age = ref<number | ''>('')
const identity = ref('')
const preferences = ref<string[]>([])
const profileLoading = ref(false)

const GENDER_OPTIONS = ['男', '女', '保密']
const IDENTITY_OPTIONS = ['学生', '职工', '退休', '其他']
const PREFERENCE_OPTIONS = ['美食', '购物', '摄影', '历史文化', '自然风光', '户外运动', '艺术展览', '夜生活']

const users = ref<AdminUser[]>([])
const usersLoading = ref(false)

onMounted(() => {
  // 加载当前用户资料
  if (userStore.user) {
    nickname.value = userStore.user.nickname || ''
    gender.value = userStore.user.gender || ''
    age.value = userStore.user.age || ''
    identity.value = userStore.user.identity || ''
    preferences.value = userStore.user.preferences || []
  }
  if (userStore.isAdmin) loadUsers()
})

function togglePreference(p: string) {
  const idx = preferences.value.indexOf(p)
  if (idx >= 0) {
    preferences.value.splice(idx, 1)
  } else {
    preferences.value.push(p)
  }
}

async function onSaveProfile() {
  profileLoading.value = true
  try {
    const { data } = await authApi.updateProfile({
      nickname: nickname.value || null,
      gender: gender.value || null,
      age: age.value === '' ? null : Number(age.value),
      identity: identity.value || null,
      preferences: preferences.value.length > 0 ? preferences.value : null,
    })
    userStore.setUser(data)
    showToast('资料已保存')
  } catch (e: any) {
    showToast(e.message || '保存失败')
  } finally {
    profileLoading.value = false
  }
}

async function onChangePwd() {
  if (!oldPwd.value || !newPwd.value) {
    showToast('请填写原密码和新密码')
    return
  }
  if (newPwd.value.length < 4) {
    showToast('新密码至少 4 位')
    return
  }
  if (newPwd.value !== confirmPwd.value) {
    showToast('两次输入的新密码不一致')
    return
  }
  pwdLoading.value = true
  try {
    await authApi.changePassword(oldPwd.value, newPwd.value)
    showToast('密码修改成功')
    oldPwd.value = ''
    newPwd.value = ''
    confirmPwd.value = ''
  } catch (e: any) {
    showToast(e.message || '修改失败')
  } finally {
    pwdLoading.value = false
  }
}

async function loadUsers() {
  usersLoading.value = true
  try {
    const { data } = await adminApi.listUsers()
    users.value = data
  } catch (e: any) {
    showToast(e.message || '加载失败')
  } finally {
    usersLoading.value = false
  }
}

async function onChangeRole(u: AdminUser, role: string) {
  if (u.id === userStore.user?.id) {
    showToast('不能修改自己的角色')
    return
  }
  try {
    await showConfirmDialog({
      title: '修改角色',
      message: `确定将「${u.username}」改为${role === 'admin' ? '管理员' : '普通用户'}吗？`,
    })
    const { data } = await adminApi.updateRole(u.id, role)
    u.role = data.role
    showToast('已更新')
  } catch {
    /* 取消 */
  }
}

function onLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="tc-page profile-page">
    <!-- 用户信息卡片 -->
    <div class="profile-card">
      <div class="profile-avatar">
        {{ (userStore.user?.nickname || userStore.user?.username || '?').charAt(0).toUpperCase() }}
      </div>
      <div class="profile-info">
        <div class="profile-name">{{ userStore.user?.nickname || userStore.user?.username }}</div>
        <div class="profile-sub">
          <span>@{{ userStore.user?.username }}</span>
          <span class="role-badge" :class="userStore.user?.role">
            {{ userStore.user?.role === 'admin' ? '管理员' : '普通用户' }}
          </span>
        </div>
      </div>
    </div>

    <!-- 个人资料 -->
    <div class="section">
      <div class="section-title">个人资料 <span class="section-hint">（选填，用于AI个性化规划）</span></div>
      <div class="form-group">
        <label>昵称</label>
        <input v-model="nickname" type="text" placeholder="请输入昵称" />
      </div>
      <div class="form-group">
        <label>性别</label>
        <div class="option-group">
          <span v-for="g in GENDER_OPTIONS" :key="g"
                class="option-tag" :class="{ active: gender === g }"
                @click="gender = g">{{ g }}</span>
        </div>
      </div>
      <div class="form-group">
        <label>年龄</label>
        <input v-model.number="age" type="number" min="1" max="120" placeholder="请输入年龄" />
      </div>
      <div class="form-group">
        <label>身份</label>
        <div class="option-group">
          <span v-for="i in IDENTITY_OPTIONS" :key="i"
                class="option-tag" :class="{ active: identity === i }"
                @click="identity = i">{{ i }}</span>
        </div>
      </div>
      <div class="form-group">
        <label>喜好（可多选）</label>
        <div class="option-group">
          <span v-for="p in PREFERENCE_OPTIONS" :key="p"
                class="option-tag" :class="{ active: preferences.includes(p) }"
                @click="togglePreference(p)">{{ p }}</span>
        </div>
      </div>
      <button class="primary-btn" :disabled="profileLoading" @click="onSaveProfile">
        {{ profileLoading ? '保存中…' : '保存资料' }}
      </button>
    </div>

    <!-- 修改密码 -->
    <div class="section">
      <div class="section-title">修改密码</div>
      <div class="form-group">
        <label>原密码</label>
        <input v-model="oldPwd" type="password" placeholder="请输入原密码" />
      </div>
      <div class="form-group">
        <label>新密码</label>
        <input v-model="newPwd" type="password" placeholder="至少 4 位" />
      </div>
      <div class="form-group">
        <label>确认新密码</label>
        <input v-model="confirmPwd" type="password" placeholder="再次输入新密码" />
      </div>
      <button class="primary-btn" :disabled="pwdLoading" @click="onChangePwd">
        {{ pwdLoading ? '提交中…' : '确认修改' }}
      </button>
    </div>

    <!-- 管理员：用户管理 -->
    <div v-if="userStore.isAdmin" class="section">
      <div class="section-title">用户管理</div>
      <div v-if="usersLoading" style="padding: 20px; text-align: center; color: #8a9a97;">加载中…</div>
      <div v-else class="user-list">
        <div v-for="u in users" :key="u.id" class="user-row">
          <div class="user-row-info">
            <span class="user-row-name">{{ u.nickname || u.username }}</span>
            <span class="user-row-sub">@{{ u.username }} · {{ u.role === 'admin' ? '管理员' : '普通用户' }}</span>
          </div>
          <div class="user-row-actions">
            <button v-if="u.role !== 'admin'" class="role-btn admin" @click="onChangeRole(u, 'admin')">设为管理员</button>
            <button v-if="u.role !== 'user'" class="role-btn user" @click="onChangeRole(u, 'user')">降为普通用户</button>
            <span v-if="u.id === userStore.user?.id" class="self-tag">当前用户</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 退出登录 -->
    <button class="logout-btn" @click="onLogout">退出登录</button>
  </div>
</template>

<style scoped>
.profile-page {
  padding-bottom: 40px;
}
.profile-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: linear-gradient(135deg, #0e7c7e, #12a5a8);
  border-radius: 14px;
  padding: 20px;
  margin-bottom: 18px;
  color: #fff;
}
.profile-avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.25);
  font-size: 22px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.profile-info {
  flex: 1;
  min-width: 0;
}
.profile-name {
  font-size: 18px;
  font-weight: 700;
}
.profile-sub {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 12px;
  opacity: 0.9;
}
.role-badge {
  padding: 1px 8px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 11px;
}
.role-badge.admin {
  background: #ff9800;
  color: #fff;
}
.role-badge.user {
  background: rgba(255, 255, 255, 0.3);
  color: #fff;
}
.section {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #e8eeec;
}
.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #1a2a27;
  margin-bottom: 14px;
}
.section-hint {
  font-size: 11px;
  font-weight: 400;
  color: #8a9a97;
}
.form-group {
  margin-bottom: 12px;
}
.form-group label {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  color: #5a6a67;
  margin-bottom: 5px;
}
.form-group input {
  width: 100%;
  box-sizing: border-box;
  padding: 9px 12px;
  border: 1px solid #d8e0de;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
}
.form-group input:focus {
  border-color: #0e7c7e;
}
.option-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.option-tag {
  padding: 6px 14px;
  border: 1px solid #d8e0de;
  border-radius: 16px;
  font-size: 13px;
  color: #5a6a67;
  cursor: pointer;
  background: #f7f9f8;
  transition: all 0.2s;
}
.option-tag.active {
  background: linear-gradient(135deg, #0e7c7e, #12a5a8);
  color: #fff;
  border-color: transparent;
}
.primary-btn {
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #0e7c7e, #12a5a8);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  margin-top: 4px;
}
.primary-btn:disabled {
  opacity: 0.6;
}
.user-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.user-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: #f7f9f8;
  border-radius: 8px;
}
.user-row-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.user-row-name {
  font-size: 14px;
  font-weight: 600;
  color: #1a2a27;
}
.user-row-sub {
  font-size: 11.5px;
  color: #8a9a97;
}
.user-row-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
.role-btn {
  border: none;
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
}
.role-btn.admin {
  background: #fff3e0;
  color: #e65100;
}
.role-btn.user {
  background: #e8f5e9;
  color: #2e7d32;
}
.self-tag {
  font-size: 11px;
  color: #b0bcb9;
  font-weight: 600;
}
.logout-btn {
  width: 100%;
  padding: 12px;
  border: 1px solid #f5c6c6;
  background: #fff;
  color: #d32f2f;
  font-size: 14px;
  font-weight: 700;
  border-radius: 10px;
  cursor: pointer;
}
</style>
