import { useEffect, useMemo, useReducer, useRef, type Dispatch, type ReactNode } from 'react'
import { api } from '../api/endpoints'
import { useSimSocket } from '../api/useSimSocket'
import { initialLiveState, liveReducer, TRADES_KEPT, type LiveAction } from '../hooks/liveReducer'
import { LiveContext, type LiveContextValue } from '../hooks/useLive'
import { historySteps } from '../lib/simState'
import type { SimStatus, SocketMessage } from '../types/api'

const STATUS_POLL_MS = 10_000

// the socket only pushes new steps; the day so far and the last trades come from REST
function loadDay(status: SimStatus, dispatch: Dispatch<LiveAction>): void {
  api.history(historySteps(status)).then((res) => dispatch({ type: 'history', steps: res.steps }), () => {})
  api.recentTrades(TRADES_KEPT).then((res) => dispatch({ type: 'trades', trades: res.transactions }), () => {})
}

export function LiveProvider({ token, children }: { token: string; children: ReactNode }) {
  const [state, dispatch] = useReducer(liveReducer, initialLiveState)
  const connectedBefore = useRef(false)

  const connection = useSimSocket(token, (msg: SocketMessage) => {
    if (msg.type === 'step') dispatch({ type: 'step', step: msg.data, status: msg.status })
    else if (msg.type === 'connected') {
      dispatch({ type: 'status', status: msg.status })
      if (msg.last) dispatch({ type: 'step', step: msg.last })
      // the steps simulated while the socket was down (API restart, deploy) were never pushed
      if (connectedBefore.current) loadDay(msg.status, dispatch)
      connectedBefore.current = true
    } else dispatch({ type: 'status', status: msg.status })
  })

  useEffect(() => {
    let cancelled = false
    api.status().then((status) => {
      if (cancelled) return
      dispatch({ type: 'status', status })
      loadDay(status, dispatch)
    }, () => {})
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
