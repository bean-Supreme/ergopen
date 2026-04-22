import { useState } from 'react'
import FftChart from '@/components/FftChart'
import WaveformCanvas from '@/components/WaveformCanvas'
import { startCapture, startRecording, stopCapture, stopRecording } from '@/lib/ergopen/types'
import { useStream } from '@/lib/ergopen/useStream'
import { cn } from '@/lib/utils'

const EMPTY_WAVEFORM = Array(512).fill(0) as number[]
const EMPTY_FFT      = [] as number[]

export default function Debug() {
  const { connected, frame, config, fftFreqs } = useStream()
  const [capturing, setCapturing] = useState(false)

  const waveform = frame?.waveform ?? EMPTY_WAVEFORM
  const fftMag   = frame?.fft_mag  ?? EMPTY_FFT

  return (
    <div className="min-h-screen bg-[#09090b] text-foreground flex flex-col font-mono">

      {/* Header */}
      <header className="flex items-center gap-3 px-5 py-3 border-b border-border/40">
        <span className="text-sm font-semibold tracking-widest text-muted-foreground uppercase">
          ergopen
        </span>
        <span className="text-muted-foreground/30">·</span>
        <span className="text-xs text-muted-foreground">debug</span>
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

      {/* Main grid */}
      <div className="flex flex-1 overflow-hidden">

        {/* Left — charts */}
        <div className="flex flex-col flex-1 gap-px bg-border/20">

          {/* Waveform */}
          <section className="flex flex-col bg-[#09090b] px-4 pt-3 pb-2" style={{ height: '40%' }}>
            <SectionLabel>waveform · last 100ms · normalized</SectionLabel>
            <div className="flex-1 mt-2">
              <WaveformCanvas waveform={waveform} />
            </div>
          </section>

          {/* FFT */}
          <section className="flex flex-col bg-[#09090b] px-4 pt-3 pb-2" style={{ height: '60%' }}>
            <SectionLabel>fft spectrum · 50–600 Hz</SectionLabel>
            {frame?.freq && (
              <span className="text-[10px] text-yellow-400/70 ml-auto -mt-4">
                peak ≈ {frame.freq.toFixed(1)} Hz
              </span>
            )}
            <div className="flex-1 mt-2">
              <FftChart freqs={fftFreqs} mag={fftMag} />
            </div>
          </section>
        </div>

        {/* Right — readouts + controls */}
        <aside className="w-64 flex flex-col border-l border-border/40 bg-[#09090b]">

          {/* Digital readouts */}
          <div className="flex-1 px-4 py-3 space-y-px overflow-y-auto">
            <SectionLabel>signal</SectionLabel>
            <Readout label="RMS"    value={frame ? frame.rms.toFixed(0)  : '—'} highlight={frame?.is_active} />
            <Readout label="freq"   value={frame?.freq  ? `${frame.freq.toFixed(2)} Hz`  : '—'} accent />
            <Readout label="active" value={frame ? (frame.is_active ? 'YES' : 'no') : '—'}
                     highlight={frame?.is_active} />

            <div className="pt-3" />
            <SectionLabel>derived</SectionLabel>
            <Readout label="RPM"   value={frame?.rpm   ? frame.rpm.toFixed(1)           : '—'} accent />
            <Readout label="watts" value={frame?.watts ? `${frame.watts.toFixed(2)} W`  : '—'} />
            <Readout label="PPR"   value={config ? String(config.ppr) : '—'} />

            <div className="pt-3" />
            <SectionLabel>stream</SectionLabel>
            <Readout label="ts"       value={frame ? frame.ts.toFixed(3) : '—'} mono />
            <Readout label="rec"      value={frame?.is_recording ? `${frame.rec_duration.toFixed(1)}s` : 'off'} />
            <Readout label="waveform" value={`${waveform.length} pts`} />
            <Readout label="fft bins" value={fftMag.length ? `${fftMag.length} pts` : '—'} />
          </div>

          {/* Controls */}
          <div className="border-t border-border/40 px-4 py-3 space-y-2">
            <SectionLabel>controls</SectionLabel>
            <DebugButton
              onClick={() => {
                capturing ? stopCapture() : startCapture()
                setCapturing(c => !c)
              }}
              variant={capturing ? 'destructive' : 'default'}
            >
              {capturing ? 'stop capture' : 'start capture'}
            </DebugButton>
            <DebugButton
              onClick={() => frame?.is_recording ? stopRecording() : startRecording()}
              variant={frame?.is_recording ? 'destructive' : 'default'}
            >
              {frame?.is_recording ? 'stop recording' : 'start recording'}
            </DebugButton>
          </div>
        </aside>
      </div>
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] uppercase tracking-widest text-muted-foreground/50 pb-1">
      {children}
    </p>
  )
}

function Readout({
  label,
  value,
  accent = false,
  highlight = false,
  mono = true,
}: {
  label: string
  value: string
  accent?: boolean
  highlight?: boolean
  mono?: boolean
}) {
  return (
    <div className="flex items-baseline justify-between py-0.5">
      <span className="text-[11px] text-muted-foreground/60 shrink-0 pr-2">{label}</span>
      <span className={cn(
        'text-sm tabular-nums truncate text-right',
        mono && 'font-mono',
        accent && 'text-cyan-300',
        highlight && 'text-green-300',
        !accent && !highlight && 'text-foreground/80',
      )}>
        {value}
      </span>
    </div>
  )
}

function DebugButton({
  children,
  onClick,
  variant = 'default',
}: {
  children: React.ReactNode
  onClick: () => void
  variant?: 'default' | 'destructive'
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left text-xs px-2 py-1.5 rounded border font-mono transition-colors',
        variant === 'default'
          ? 'border-border/50 text-muted-foreground hover:text-foreground hover:border-border'
          : 'border-red-900/50 text-red-400 hover:border-red-700',
      )}
    >
      {children}
    </button>
  )
}
