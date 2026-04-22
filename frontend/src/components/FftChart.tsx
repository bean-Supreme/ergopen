import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useMemo } from 'react'

interface Props {
  freqs: number[]   // Hz axis (50–600 Hz)
  mag: number[]     // magnitudes
}

export default function FftChart({ freqs, mag }: Props) {
  const data = useMemo(
    () => freqs.map((f, i) => ({ hz: Math.round(f), mag: mag[i] ?? 0 })),
    [freqs, mag],
  )

  const yMax = useMemo(() => {
    const m = Math.max(...mag, 1)
    return Math.ceil(m * 1.15)
  }, [mag])

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="fftGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#ff6b6b" stopOpacity={0.4} />
            <stop offset="95%" stopColor="#ff6b6b" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="hz"
          tick={{ fill: '#555577', fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          interval={Math.floor(freqs.length / 6)}
          tickFormatter={(v) => `${v}Hz`}
        />
        <YAxis
          domain={[0, yMax]}
          tick={false}
          axisLine={false}
          tickLine={false}
          width={0}
        />
        <Tooltip
          contentStyle={{ background: '#16161d', border: '1px solid #333', fontSize: 11 }}
          formatter={(v) => [Number(v).toFixed(0), 'mag']}
          labelFormatter={(hz) => `${hz} Hz`}
        />
        <Area
          type="monotone"
          dataKey="mag"
          stroke="#ff6b6b"
          strokeWidth={1.5}
          fill="url(#fftGrad)"
          isAnimationActive={false}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
