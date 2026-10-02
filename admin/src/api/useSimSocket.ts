import { useEffect, useEffectEvent, useState } from 'react'
import { ApiError } from './client'
import { api } from './endpoints'
import type { SocketMessage } from '../types/api'

export type ConnectionState = 'connecting' | 'open' | 'closed'

const PING_MS = 25_000
const BACKOFF_BASE_MS = 1_000
const BACKOFF_MAX_MS = 30_000

export function backoffDelay(attempt: number): number {
  return Math.min(BACKOFF_MAX_MS, BACKOFF_BASE_MS * 2 ** attempt)
}

export function socketUrl(token: string, loc: Pick<Location, 'protocol' | 'host'> = window.location): string {
  const scheme = loc.protocol === 'https:' ? 'wss' : 'ws'
  return `${scheme}://${loc.host}/api/admin/ws?token=${encodeURIComponent(token)}`
}

export function parseMessage(raw: unknown): SocketMessage | null {
  if (typeof raw !== 'string' || raw === 'pong') return null
  try {
    const msg = JSON.parse(raw) as SocketMessage
    return msg && typeof msg === 'object' && 'type' in msg ? msg : null
  } catch {
    return null
  }
}

export interface SocketInfo {
  state: ConnectionState
  retryInSeconds: number | null
}

export function useSimSocket(token: string, onMessage: (msg: SocketMessage) => void): SocketInfo {
  const [info, setInfo] = useState<SocketInfo>({ state: 'connecting', retryInSeconds: null })
  const handleMessage = useEffectEvent(onMessage)

  useEffect(() => {
    let ws: WebSocket | null = null
    let attempt = 0
    let pingTimer: number | undefined
    let retryTimer: number | undefined
    let disposed = false

    const connect = () => {
      ws = new WebSocket(socketUrl(token))
      ws.onopen = () => {
        attempt = 0
        setInfo({ state: 'open', retryInSeconds: null })
        pingTimer = window.setInterval(() => ws?.readyState === WebSocket.OPEN && ws.send('ping'), PING_MS)
      }
      ws.onmessage = (ev) => {
        const msg = parseMessage(ev.data)
        if (msg) handleMessage(msg)
      }
      ws.onclose = () => {
        window.clearInterval(pingTimer)
        if (!disposed) scheduleReconnect()
      }
    }

    const scheduleReconnect = () => {
      const delay = backoffDelay(attempt++)
      setInfo({ state: 'closed', retryInSeconds: Math.round(delay / 1000) })
      retryTimer = window.setTimeout(async () => {
        setInfo({ state: 'connecting', retryInSeconds: null })
        // an expired token also closes the socket (code 1008); /me then triggers the 401 logout
        try {
          await api.me()
        } catch (e) {
          if (e instanceof ApiError && e.status === 401) return
        }
        if (!disposed) connect()
      }, delay)
    }

    connect()
    return () => {
      disposed = true
      window.clearInterval(pingTimer)
      window.clearTimeout(retryTimer)
      const socket = ws
      if (socket?.readyState === WebSocket.CONNECTING) {
        // closing a socket that is still connecting makes the browser log an error; close it once open
        socket.onopen = () => socket.close()
        socket.onmessage = null
      } else {
        socket?.close()
      }
    }
  }, [token])

  return info
}
