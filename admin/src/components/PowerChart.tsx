import { Area, AreaChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from 'recharts'
import { formatHour, formatNumber } from '../lib/format'
import { HOUR_TICKS, powerSeries } from '../lib/series'
import type { StepResult } from '../types/api'
import { ChartTooltip } from './ChartTooltip'

const SERIES = [
  { key: 'pv', name: 'Producție PV', color: 'var(--series-pv)' },
  { key: 'load', name: 'Consum', color: 'var(--series-load)' },
  { key: 'import', name: 'Import rețea', color: 'var(--series-import)' },
  { key: 'export', name: 'Export rețea', color: 'var(--series-export)' },
] as const

export function PowerChart({ day, height = 300 }: { day: StepResult[]; height?: number }) {
  const data = powerSeries(day)
  return (
    <div data-testid="power-chart" data-points={data.length}>
      <AreaChart responsive data={data} style={{ width: '100%', height }} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
        <defs>
          {SERIES.map((s) => (
            <linearGradient key={s.key} id={`fill-${s.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s.color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={s.color} stopOpacity={0.02} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="hour"
          type="number"
          domain={[0, 24]}
          ticks={HOUR_TICKS}
          tickFormatter={formatHour}
          stroke="var(--text-3)"
          tick={{ fontSize: 12 }}
        />
        <YAxis
          stroke="var(--text-3)"
          tick={{ fontSize: 12 }}
          tickFormatter={(v: number) => `${formatNumber(v, 1)} kW`}
          width={64}
        />
        <Tooltip content={<ChartTooltip unit="kW" />} />
        <Legend iconType="square" iconSize={9} itemSorter={null} wrapperStyle={{ fontSize: 13 }} />
        {SERIES.map((s) => (
          <Area
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.name}
            stroke={s.color}
            strokeWidth={2}
            fill={`url(#fill-${s.key})`}
            isAnimationActive={false}
            dot={false}
          />
        ))}
      </AreaChart>
    </div>
  )
}
