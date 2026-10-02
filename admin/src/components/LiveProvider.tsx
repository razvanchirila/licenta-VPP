import { useEffect, useMemo, useReducer, type ReactNode } from 'react'
import { api } from '../api/endpoints'
import { useSimSocket } from '../api/useSimSocket'
import { initialLiveState, liveReducer } from '../hooks/liveReducer'
import { LiveContext, type LiveContextValue } from '../hooks/useLive'
import type { SocketMessage } from '../types/api'

const STATUS_POLL_MS = 10_000

export function LiveProvider({ token, children }: { token: string; children: ReactNode }) {
  const [state, dispatch] = useReducer(liveReducer, initialLiveState)

  const connection = useSimSocket(token, (msg: SocketMessage) => {
    if (msg.type === 'step') dispatch({ type: 'step', step: msg.data, status: msg.status })
    else if (msg.type === 'connected') {
      dispatch({ type: 'status', status: msg.status })
      if (msg.last) dispatch({ type: 'step', step: msg.last })
    } else dispatch({ type: 'status', status: msg.status })
  })

  // the socket only pushes new steps; the day so far and the last trades come from REST once
  useEffect(() => {
    let cancelled = false
    api.history(96).then((res) => !cancelled && dispatch({ type: 'history', steps: res.steps }), () => {})
    api.recentTrades(20).then((res) => !cancelled && dispatch({ type: 'trades', trades: res.transactions }), () => {})
    api.status().then((status) => !cancelled && dispatch({ type: 'status', status }), () => {})
    return () => {
      cancelled = true
    }
  }, [])

  // a paused or stopped loop sends no steps, so a pause made elsewhere would otherwise go unnoticed
  useEffect(() => {
    const timer = window.setInterval(() => {
      api.status().then((status) => dispatch({ type: 'status', status }), () => {})
    }, STATUS_POLL_MS)
    return () => window.clearInterval(timer)
  }, [])

  const value = useMemo<LiveContextValue>(
    () => ({ ...state, last: state.day[state.day.length - 1] ?? null, connection, dispatch }),
    [state, connection],
  )
  return <LiveContext value={value}>{children}</LiveContext>
}
