import { request, requestText } from './client'
import type {
  DayPrices,
  Device,
  EditableConfig,
  House,
  HouseMode,
  HouseSpec,
  LoginResponse,
  Me,
  MessageResponse,
  Neighbourhood,
  SimConfig,
  SimStatus,
  StepResult,
  Trade,
  VppStats,
  Wallet,
} from '../types/api'

type StatusResponse = MessageResponse & { status: SimStatus }

export const api = {
  login: (username: string, password: string) =>
    request<LoginResponse>('/api/auth/login', { method: 'POST', body: { username, password }, auth: false }),
  me: () => request<Me>('/api/auth/me'),

  status: () => request<SimStatus>('/api/sim/status'),
  history: (limit = 96) => request<{ count: number; steps: StepResult[] }>(`/api/sim/history?limit=${limit}`),
  prices: () => request<DayPrices>('/api/sim/prices'),
  simAction: (action: 'start' | 'stop' | 'pause' | 'resume' | 'reset') =>
    request<StatusResponse>(`/api/sim/${action}`, { method: 'POST' }),
  step: () => request<StepResult>('/api/sim/step', { method: 'POST' }),
  speed: (tickSeconds: number) =>
    request<MessageResponse>('/api/sim/speed', { method: 'POST', body: { tick_seconds: tickSeconds } }),

  vppStats: () => request<VppStats>('/api/vpp/stats'),
  recentTrades: (limit = 20) => request<{ count: number; transactions: Trade[] }>(`/api/trading/recent?limit=${limit}`),

  houses: () => request<House[]>('/api/houses'),
  house: (id: number) => request<House>(`/api/houses/${id}`),
  wallet: (houseId: number) => request<Wallet>(`/api/wallet/${houseId}`),
  setMode: (houseId: number, mode: HouseMode) =>
    request<MessageResponse & { mode: HouseMode }>(`/api/houses/${houseId}/mode`, { method: 'POST', body: { mode } }),
  toggleDevice: (houseId: number, deviceId: number) =>
    request<Device>(`/api/houses/${houseId}/devices/${deviceId}/toggle`, { method: 'POST' }),

  neighbourhood: () => request<Neighbourhood>('/api/admin/neighbourhood'),
  saveHouseSpec: ({ id, ...body }: HouseSpec) =>
    request<HouseSpec>(`/api/admin/neighbourhood/${id}`, { method: 'PUT', body }),
  resetNeighbourhood: () => request<MessageResponse>('/api/admin/neighbourhood/reset', { method: 'POST' }),
  exportNeighbourhood: () => requestText('/api/admin/neighbourhood/export'),

  config: () => request<SimConfig>('/api/config'),
  updateConfig: (changes: Partial<EditableConfig>) =>
    request<MessageResponse & { config: SimConfig }>('/api/config', { method: 'PUT', body: changes }),
  resetConfig: () => request<MessageResponse & { config: SimConfig }>('/api/config/reset', { method: 'POST' }),
}
