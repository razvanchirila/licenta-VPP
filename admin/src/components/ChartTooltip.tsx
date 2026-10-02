import { formatHour, formatNumber } from '../lib/format'
import styles from './ChartTooltip.module.css'

interface TooltipEntry {
  name?: string | number
  value?: number | string | readonly (number | string)[]
  color?: string
  dataKey?: unknown
}

interface ChartTooltipProps {
  active?: boolean
  label?: number | string
  payload?: readonly TooltipEntry[]
  unit: string
  digits?: number
}

export function ChartTooltip({ active, label, payload, unit, digits = 2 }: ChartTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div className={styles.box}>
      <div className={styles.title}>{formatHour(Number(label))}</div>
      {payload.map((entry) => (
        <div key={String(entry.dataKey)} className={styles.row}>
          <i style={{ background: entry.color }} aria-hidden />
          <span>{entry.name}</span>
          <strong className="num">
            {formatNumber(Number(entry.value), digits)} {unit}
          </strong>
        </div>
      ))}
    </div>
  )
}
