import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, Tooltip, XAxis, YAxis } from 'recharts'
import { formatHour, formatNumber } from '../lib/format'
import { HOUR_TICKS, priceSeries } from '../lib/series'
import type { DayPrices } from '../types/api'
import { ChartTooltip } from './ChartTooltip'

const SERIES = [
  { key: 'import', name: 'Import', color: 'var(--series-import)' },
  { key: 'export', name: 'Export', color: 'var(--series-export)' },
  { key: 'p2p', name: 'P2P', color: 'var(--series-p2p)' },
] as const

export function PriceChart({ prices, nowHour, height = 260 }: { prices?: DayPrices; nowHour: number | null; height?: number }) {
  const data = priceSeries(prices)
  return (
    <LineChart responsive data={data} style={{ width: '100%', height }} margin={{ top: 16, right: 8, left: -8, bottom: 0 }}>
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
      <YAxis stroke="var(--text-3)" tick={{ fontSize: 12 }} tickFormatter={(v: number) => formatNumber(v, 2)} width={56} />
      <Tooltip content={<ChartTooltip unit="lei/kWh" digits={3} />} />
      <Legend iconType="plainline" itemSorter={null} wrapperStyle={{ fontSize: 13 }} />
      {SERIES.map((s) => (
        <Line
          key={s.key}
          type="stepAfter"
          dataKey={s.key}
          name={s.name}
          stroke={s.color}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      ))}
      {nowHour !== null && (
        <ReferenceLine
          x={nowHour}
          stroke="var(--text)"
          strokeDasharray="4 4"
          label={{ value: 'acum', position: 'top', fill: 'var(--text-2)', fontSize: 12 }}
        />
      )}
    </LineChart>
  )
}
