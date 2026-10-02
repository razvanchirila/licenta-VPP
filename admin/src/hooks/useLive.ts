import { createContext, useContext, type Dispatch } from 'react'
import type { SocketInfo } from '../api/useSimSocket'
import type { SimStatus, StepResult, Trade } from '../types/api'
import type { LiveAction } from './liveReducer'

export interface LiveContextValue {
  status: SimStatus | null
  day: StepResult[]
  last: StepResult | null
  trades: Trade[]
  connection: SocketInfo
  dispatch: Dispatch<LiveAction>
}

export const LiveContext = createContext<LiveContextValue | null>(null)

export function useLive(): LiveContextValue {
  const ctx = useContext(LiveContext)
  if (!ctx) throw new Error('useLive must be used inside LiveProvider')
  return ctx
}
