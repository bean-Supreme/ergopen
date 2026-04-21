import { useEffect, useRef, useState } from 'react'
import type { Config, ServerMessage, SignalFrame } from './types'
import { WS_URL } from './types'

export interface StreamState {
  connected: boolean
  frame: SignalFrame | null
  config: Config | null
  fftFreqs: number[]
}

export function useStream(): StreamState {
  const [connected, setConnected] = useState(false)
  const [frame, setFrame]         = useState<SignalFrame | null>(null)
  const [config, setConfig]       = useState<Config | null>(null)
  const [fftFreqs, setFftFreqs]   = useState<number[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    let ws: WebSocket
    let dead = false

    function connect() {
      ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)

      ws.onmessage = (e: MessageEvent<string>) => {
        const msg = JSON.parse(e.data) as ServerMessage
        if (msg.type === 'init') {
          setFftFreqs(msg.fft_freqs)
          setConfig(msg.config)
        } else if (msg.type === 'frame') {
          setFrame(msg.data)
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (!dead) setTimeout(connect, 2000)  // auto-reconnect
      }

      ws.onerror = () => ws.close()
    }

    connect()
    return () => {
      dead = true
      ws?.close()
    }
  }, [])

  return { connected, frame, config, fftFreqs }
}
