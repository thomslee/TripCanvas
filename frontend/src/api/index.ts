import axios from 'axios'

const TOKEN_KEY = 'tripcanvas_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

const http = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (resp) => resp,
  (err) => {
    if (err?.response?.status === 401) {
      setToken(null)
      if (location.pathname !== '/login') location.href = '/login'
    }
    const msg = err?.response?.data?.detail || err.message || '请求失败'
    return Promise.reject(new Error(msg))
  },
)

export interface TripDay {
  id: number
  day_no: number
  date: string | null
  theme: string | null
  city: string | null
}

export interface DestCity {
  city: string
  days: number
}

export interface Trip {
  id: number
  title: string | null
  depart_city: string
  dest_city: string
  depart_date: string
  arrive_time: string | null
  return_date: string
  depart_time: string | null
  total_days: number
  status: string
  preferences: Record<string, unknown> | null
  dest_cities: DestCity[] | null
  ai_version: string | null
  created_at: string
  days: TripDay[]
}

export interface DayWindow {
  day_no: number
  date: string
  start: string
  end: string
  note: string
}

export interface TripCreatePayload {
  depart_city: string
  dest_city: string
  depart_date: string
  arrive_time?: string | null
  return_date: string
  depart_time?: string | null
  preferences?: Record<string, unknown>
  dest_cities?: DestCity[]
}

export interface TripCreateResult {
  trip: Trip
  windows: DayWindow[]
  messages: string[]
}

export type NodeType = 'hotel' | 'attraction' | 'restaurant'
export type Transport = 'walk' | 'taxi' | 'bus' | 'metro' | 'bike' | 'car' | 'train' | 'ship' | 'plane'

export interface Poi {
  id: number
  city: string | null
  poi_type: NodeType
  name: string
  address: string | null
  open_hours: string | null
  ticket_price: string | null
  rating: number | null
  source: string | null
}

export interface ItineraryNode {
  id: number
  node_type: NodeType
  name: string
  duration_minutes: number
  sort_order: number
  note: string | null
  poi_id: number | null
  poi: Poi | null
  start_time: string | null
  end_time: string | null
}

export interface TripPoi {
  poi: Poi
  count: number
  node_ids: number[]
}

export interface ItineraryEdge {
  id: number
  from_node_id: number
  to_node_id: number
  transport: Transport
  duration_minutes: number
  note: string | null
}

export interface DayTimeline {
  day_no: number
  date: string
  city: string | null
  window_start: string
  window_end: string
  note: string
  total_used_min: number
  conflict: boolean
  overflow_min: number
  nodes: ItineraryNode[]
  edges: ItineraryEdge[]
}

export interface Timeline {
  trip_id: number
  title: string | null
  dest_city: string | null
  dest_cities: DestCity[] | null
  days: DayTimeline[]
}

export interface NodeCreatePayload {
  node_type: NodeType
  name: string
  duration_minutes: number
  note?: string | null
  poi_id?: number | null
  after_node_id?: number | null
}

export const tripsApi = {
  create: (data: TripCreatePayload) => http.post<TripCreateResult>('/trips', data),
  list: () => http.get<Trip[]>('/trips'),
  get: (id: number) => http.get<Trip>(`/trips/${id}`),
  remove: (id: number) => http.delete(`/trips/${id}`),
  patch: (id: number, payload: Record<string, unknown>) => http.patch<Trip>(`/trips/${id}`, payload),
  duplicate: (id: number) => http.post<Trip>(`/trips/${id}/duplicate`),
}

export const timelineApi = {
  seed: (tripId: number) => http.post<{ seeded: boolean; message: string }>(`/trips/${tripId}/seed`),
  get: (tripId: number) => http.get<Timeline>(`/trips/${tripId}/timeline`),
  addNode: (tripId: number, dayNo: number, payload: NodeCreatePayload) =>
    http.post<ItineraryNode>(`/trips/${tripId}/days/${dayNo}/nodes`, payload),
  patchNode: (nodeId: number, payload: Partial<Omit<ItineraryNode, 'id' | 'sort_order' | 'poi' | 'start_time' | 'end_time'>>) =>
    http.patch<ItineraryNode>(`/nodes/${nodeId}`, payload),
  deleteNode: (nodeId: number) => http.delete(`/nodes/${nodeId}`),
  moveNode: (nodeId: number, direction: 'up' | 'down') =>
    http.post(`/nodes/${nodeId}/move`, { direction }),
  patchEdge: (edgeId: number, payload: { transport?: Transport; duration_minutes?: number }) =>
    http.patch<ItineraryEdge>(`/edges/${edgeId}`, payload),
  reorder: (tripId: number, dayNo: number, nodeIds: number[]) =>
    http.post(`/trips/${tripId}/days/${dayNo}/reorder`, { node_ids: nodeIds }),
}

export const poiApi = {
  search: (params: { city?: string; q?: string; type?: NodeType; limit?: number }) =>
    http.get<Poi[]>('/pois/search', { params }),
  seed: () => http.post('/pois/seed'),
  listTrip: (tripId: number) => http.get<TripPoi[]>(`/trips/${tripId}/pois`),
  deleteTrip: (tripId: number, poiId: number) => http.delete(`/trips/${tripId}/pois/${poiId}`),
}

export interface WeatherForecast {
  date: string
  desc: string
  icon: string
  temp_min: number | null
  temp_max: number | null
}

export interface Weather {
  available: boolean
  city: string
  date: string | null
  desc: string
  icon: string
  temp: number | null
  feels: number | null
  temp_min: number | null
  temp_max: number | null
  advice?: string | null
  forecast?: WeatherForecast[]
  message?: string
}

export interface ReplanResult {
  applied: boolean
  summary: string
  notes: string[]
  timeline: Timeline
}

export const weatherApi = {
  get: (city: string) => http.get<Weather>('/weather', { params: { city } }),
}

export interface AppSettings {
  llm_base_url: string
  llm_api_key: string
  llm_model: string
  amap_key: string
  weather_provider: string
}

export const settingsApi = {
  get: () => http.get<AppSettings>('/settings'),
  update: (data: Partial<AppSettings>) => http.put<AppSettings>('/settings', data),
}

export const replanApi = {
  run: (tripId: number) => http.post<ReplanResult>(`/trips/${tripId}/replan`),
}

export interface AIPlanResult {
  generated: boolean
  total_nodes: number
  poi_matched: number
  days: number
  source: string
  timeline: Timeline
}

export const aiPlanApi = {
  run: (tripId: number) => http.post<AIPlanResult>(`/trips/${tripId}/ai-plan`),
}

export interface AuthUser {
  id: number
  username: string
  nickname: string | null
  role: 'admin' | 'user'
}

export interface AuthResult {
  token: string
  user: AuthUser
}

export const authApi = {
  login: (username: string, password: string) =>
    http.post<AuthResult>('/auth/login', { username, password }),
  register: (username: string, password: string, nickname?: string) =>
    http.post<AuthResult>('/auth/register', { username, password, nickname }),
  me: () => http.get<AuthUser>('/auth/me'),
  changePassword: (old_password: string, new_password: string) =>
    http.put('/auth/me/password', { old_password, new_password }),
}

export interface AdminUser {
  id: number
  username: string
  nickname: string | null
  role: 'admin' | 'user'
  created_at: string | null
}

export const adminApi = {
  listUsers: () => http.get<AdminUser[]>('/admin/users'),
  updateRole: (userId: number, role: string) =>
    http.patch<AdminUser>(`/admin/users/${userId}`, { role }),
}

export default http
