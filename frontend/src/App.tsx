import { useStream } from '@/lib/ergopen/useStream'

export default function App() {
  const { connected, frame, config } = useStream()

  return (
    <div className="min-h-screen bg-background text-foreground p-8 font-mono">
      <header className="mb-8 flex items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">ergopen</h1>
        <span
          className={`h-2 w-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}
          title={connected ? 'connected' : 'disconnected'}
        />
        <span className="text-xs text-muted-foreground">
          {connected ? 'connected' : 'connecting…'}
        </span>
      </header>

      <div className="grid grid-cols-2 gap-4 max-w-2xl">
        <Stat label="RMS"    value={frame ? frame.rms.toFixed(0)              : '—'} />
        <Stat label="Freq"   value={frame?.freq  ? `${frame.freq.toFixed(1)} Hz` : '—'} />
        <Stat label="RPM"    value={frame?.rpm   ? frame.rpm.toFixed(0)          : '—'} />
        <Stat label="Watts"  value={frame?.watts ? `${frame.watts.toFixed(1)} W` : '—'} />
        <Stat label="PPR"    value={config ? String(config.ppr) : '—'} />
        <Stat label="Active" value={frame ? (frame.is_active ? 'yes' : 'no') : '—'} />
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className="text-xl font-semibold tabular-nums">{value}</div>
    </div>
  )
}
