import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, setToken, getToken, type AuthUser } from '../api'

export const useUserStore = defineStore('user', () => {
  const user = ref<AuthUser | null>(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(username: string, password: string) {
    const { data } = await authApi.login(username, password)
    setToken(data.token)
    user.value = data.user
    return data.user
  }

  async function register(username: string, password: string, nickname?: string) {
    const { data } = await authApi.register(username, password, nickname)
    setToken(data.token)
    user.value = data.user
    return data.user
  }

  async function fetchMe() {
    if (!getToken()) return null
    try {
      const { data } = await authApi.me()
      user.value = data
      return data
    } catch {
      setToken(null)
      user.value = null
      return null
    }
  }

  function logout() {
    setToken(null)
    user.value = null
  }

  function setUser(u: AuthUser) {
    user.value = u
  }

  return { user, loading, isLoggedIn, isAdmin, login, register, fetchMe, logout, setUser }
})
