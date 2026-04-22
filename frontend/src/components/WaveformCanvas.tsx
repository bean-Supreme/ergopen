import { useEffect, useRef } from 'react'

interface Props {
  waveform: number[]   // 512 points, normalized [-1, 1]
  color?: string
}

export default function WaveformCanvas({ waveform, color = '#00d4ff' }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Resize canvas to match container on mount and window resize
  useEffect(() => {
    const container = containerRef.current
    const canvas = canvasRef.current
    if (!container || !canvas) return

    const obs = new ResizeObserver(() => {
      canvas.width  = container.clientWidth
      canvas.height = container.clientHeight
    })
    obs.observe(container)
    canvas.width  = container.clientWidth
    canvas.height = container.clientHeight
    return () => obs.disconnect()
  }, [])

  // Draw on every frame update
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || waveform.length === 0) return
    const ctx = canvas.getContext('2d')!
    const { width, height } = canvas

    ctx.fillStyle = '#0a0a0f'
    ctx.fillRect(0, 0, width, height)

    // Zero line
    ctx.beginPath()
    ctx.strokeStyle = '#1e1e2e'
    ctx.lineWidth = 1
    ctx.moveTo(0, height / 2)
    ctx.lineTo(width, height / 2)
    ctx.stroke()

    // Waveform
    ctx.beginPath()
    ctx.strokeStyle = color
    ctx.lineWidth = 1.5
    ctx.lineJoin = 'round'

    waveform.forEach((v, i) => {
      const x = (i / (waveform.length - 1)) * width
      const y = ((1 - v) / 2) * height
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    })

    ctx.stroke()
  }, [waveform, color])

  return (
    <div ref={containerRef} className="w-full h-full">
      <canvas ref={canvasRef} className="block w-full h-full" />
    </div>
  )
}
