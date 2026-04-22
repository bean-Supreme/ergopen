import { useState } from 'react'
import { Link } from 'react-router-dom'
import { startCapture, stopCapture } from '@/lib/ergopen/types'
import { useStream } from '@/lib/ergopen/useStream'
import { cn } from '@/lib/utils'

function formatSplit(sec: number): string {
  const m   = Math.floor(sec / 60)
  const s   = Math.floor(sec % 60)
  const d   = Math.floor((sec % 1) * 10)
  return `${m}:${String(s).padStart(2, '0')}.${d}`
}

export default function Dashboard() {
  const { connected, frame } = useStream()
  const [capturing, setCapturing] = useState(false)

  const split = frame?.split_sec != null ? formatSplit(frame.split_sec) : null

  return (
    <div className="min-h-screen bg-[#09090b] text-foreground flex flex-col font-mono">

      {/* Header */}
      <header className="flex items-center gap-3 px-5 py-3 border-b border-border/40">
        <span className="text-sm font-semibold tracking-widest text-muted-foreground uppercase">
          ergopen
        </span>
        <div className="ml-auto flex items-center gap-4">
          {frame?.is_recording && (
            <span className="flex items-center gap-1.5 text-xs text-red-400 animate-pulse">
              <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
              REC {frame.rec_duration.toFixed(1)}s
            </span>
          )}
          <span className={cn('flex items-center gap-1.5 text-xs', connected ? 'text-green-400' : 'text-red-400')}>
            <span className={cn('h-1.5 w-1.5 rounded-full', connected ? 'bg-green-400' : 'bg-red-400')} />
            {connected ? 'connected' : 'disconnected'}
          </span>
        </div>
      </header>

      {/* Metrics */}
      <div className="flex flex-1 flex-col items-center justify-center gap-12 px-8">

        {/* Hero — Split */}
        <div className="flex flex-col items-center gap-1">
          <span className="text-[10px] uppercase tracking-widest text-muted-foreground/50">
            split / 500m
          </span>
          <span className={cn(
            'text-8xl tabular-nums font-light tracking-tight',
            split ? 'text-foreground' : 'text-muted-foreground/20',
          )}>
            {split ?? '--:--.-'}
          </span>
        </div>

        {/* Secondary row — SPM · Watts · RPM */}
        <div className="flex gap-12 md:gap-20">
          <Metric label="spm"   value={frame?.spm   != null ? frame.spm.toFixed(1)          : null} />
          <Metric label="watts" value={frame?.watts  != null ? frame.watts.toFixed(0)         : null} unit="W" />
          <Metric label="rpm"   value={frame?.rpm    != null ? frame.rpm.toFixed(1)           : null} />
        </div>
      </div>

      {/* Footer — capture toggle + debug link */}
      <footer className="flex items-center justify-between px-5 pb-6">
        <Link
          to="/debug"
          className="text-[10px] uppercase tracking-widest text-muted-foreground/30 hover:text-muted-foreground transition-colors"
        >
          debug →
        </Link>
        <button
          onClick={() => { capturing ? stopCapture() : startCapture(); setCapturing(c => !c) }}
          className={cn(
            'text-[10px] uppercase tracking-widest px-3 py-1.5 rounded border font-mono transition-colors',
            capturing
              ? 'border-red-900/50 text-red-400 hover:border-red-700'
              : 'border-border/50 text-muted-foreground/50 hover:text-foreground hover:border-border',
          )}
        >
          {capturing ? 'stop' : 'start'}
        </button>
      </footer>
    </div>
  )
}

function Metric({ label, value, unit }: { label: string; value: string | null; unit?: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-[10px] uppercase tracking-widest text-muted-foreground/50">{label}</span>
      <span className={cn(
        'text-4xl tabular-nums font-light',
        value ? 'text-cyan-300' : 'text-muted-foreground/20',
      )}>
        {value ?? '—'}
        {value && unit && (
          <span className="text-xl text-muted-foreground/50 ml-1">{unit}</span>
        )}
      </span>
    </div>
  )
}
