export type Controller = 'reguli' | 'mpc'
export type DataSource = 'real' | 'sintetic'
export type HouseMode = 'Eco' | 'Profit'

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user_id: number
  username: string
  house_id: number | null
  is_admin: boolean
}

export interface Me {
  user_id: number
  username: string
  house_id: number | null
  house_name: string | null
  is_admin: boolean
  created_at: string
}

export interface SimStatus {
  running: boolean
  paused: boolean
  loaded: boolean
  controller: Controller
  data_source: DataSource
  data_year: number
  tick_seconds: number
  dt_hours: number
  total_steps: number
  sim_datetime: string
  sim_date: string
  sim_time: string
  step_of_day: number
  steps_per_day: number
  n_houses: number
  last_error: string | null
  websocket_clients: number
}

export interface StepPrice {
  import: number
  export: number
  p2p: number
}

export interface CommunityStep {
  pv_kw: number
  load_kw: number
  device_kw: number
  shed_kw: number
  curtail_kw: number
  charge_kw: number
  discharge_kw: number
  import_kw: number
  export_kw: number
  p2p_kw: number
  soc_kwh: number
  soc_percent: number
}

export interface HouseStep {
  id: number
  name: string
  mode: HouseMode
  p2p_enabled: boolean
  pv_kw: number
  load_kw: number
  device_kw: number
  shed_kw: number
  curtail_kw: number
  ch_kw: number
  dis_kw: number
  imp_kw: number
  exp_kw: number
  p2p_in_kw: number
  p2p_out_kw: number
  soc_kwh: number | null
  soc_percent: number | null
}

export type TradeStatus = 'settled' | 'rejected'

export interface StepTrade {
  seller_house_id: number
  buyer_house_id: number
  energy_kwh: number
  price_lei_kwh: number
  total_value_lei: number
  status: TradeStatus
}

export interface StepResult {
  step: number
  sim_datetime: string
  dt_h: number
  controller: Controller
  data_source: DataSource
  price: StepPrice
  community: CommunityStep
  houses: HouseStep[]
  trades: StepTrade[]
}

export interface Trade extends StepTrade {
  id?: number
  grid_price_lei_kwh?: number
  reason?: string | null
  sim_timestamp: string
}

export interface Battery {
  capacity_kwh: number
  soc_kwh: number
  soc_percent: number
  soc_min_kwh: number
  soc_max_kwh: number
  available_kwh: number
  vpp_reserve_kwh: number
  p_ch_max_kw: number
  p_dis_max_kw: number
  eta_ch: number
  eta_dis: number
}

export interface DeviceSchedule {
  mode: 'continuu' | 'zilnic' | 'ciclic' | 'termic'
  hours_per_day: number
  cycles_per_week: number
  cycle_minutes: number
  interval: string
  season: 'tot_anul' | 'iarna' | 'vara'
}

export interface Device {
  id: number
  house_id: number
  name: string
  power_w: number
  critical: boolean
  status_on: boolean
  schedule: DeviceSchedule | null
  current_power_kw: number
  accumulated_energy_kwh: number
  last_state_change_ts: string | null
}

export interface TradingPrefs {
  house_id: number
  selling_enabled: boolean
  buying_enabled: boolean
  price_mode: 'fixed' | 'discount'
  fixed_price_lei_kwh: number
  discount_percent: number
  min_sell_price_lei_kwh: number
}

export interface House {
  id: number
  name: string
  mode: HouseMode
  has_pv: boolean
  pv_capacity_kw: number
  has_battery: boolean
  battery: Battery | null
  devices: Device[]
  device_count: number
  L_crit_kw: number
  L_noncrit_kw: number
  trading: TradingPrefs | null
  wallet_balance_lei: number
  user: string | null
  last_step: HouseStep | null
}

export interface Wallet {
  house_id: number | null
  balance_lei: number
  total_earned_lei: number
  total_spent_lei: number
  net_balance_lei: number
  transaction_count: number
  vpp_reserve?: { house_id: number; reserved_kwh: number; base_rate_lei_kwh: number }
}

export interface PricePoint {
  sim_timestamp: string
  price_import: number
  price_export: number
  price_p2p: number
}

export interface DayPrices {
  date: string
  dt_hours: number
  current_step: number
  prices: PricePoint[]
}

export interface SimConfig {
  controller: Controller
  tick_seconds: number
  import_max_kw: number
  export_max_kw: number
  internal_line_kw: number
  p2p_price_factor: number
  min_p2p_balance_lei: number
  seed: number
  dt_hours: number
  data_source: DataSource
  data_year: number
  controllers: Controller[]
}

export type EditableConfig = Pick<
  SimConfig,
  | 'controller'
  | 'tick_seconds'
  | 'import_max_kw'
  | 'export_max_kw'
  | 'internal_line_kw'
  | 'p2p_price_factor'
  | 'min_p2p_balance_lei'
  | 'seed'
>

export interface VppToday {
  date: string
  pv_kwh: number
  load_kwh: number
  shed_kwh: number
  curtail_kwh: number
  import_kwh: number
  export_kwh: number
  p2p_kwh: number
  charge_kwh: number
  discharge_kwh: number
  cost_lei: number
  peak_import_kw: number
  self_consumption: number | null
  self_sufficiency: number | null
  trades_settled: number
  trades_value_lei: number
}

export interface VppStats {
  total_houses: number
  houses_with_battery: number
  total_pv_capacity_kw: number
  total_battery_capacity_kwh: number
  avg_battery_soc_percent: number
  controller: Controller
  sim_datetime: string
  today: VppToday
}

export interface MessageResponse {
  message: string
}

export type SocketMessage =
  | { type: 'connected'; status: SimStatus; last: StepResult | null }
  | { type: 'step'; data: StepResult; status: SimStatus }
  | { type: 'status'; status: SimStatus }
