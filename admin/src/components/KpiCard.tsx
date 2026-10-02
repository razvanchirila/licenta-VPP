import type { ReactNode } from 'react'
import styles from './KpiCard.module.css'

interface KpiCardProps {
  label: string
  value: ReactNode
  unit?: string
  color?: string
  hint?: string
}

export function KpiCard({ label, value, unit, color, hint }: KpiCardProps) {
  return (
    <div className={styles.kpi} title={hint} data-testid="kpi">
      <span className={styles.label}>
        {color && <i className={styles.swatch} style={{ background: color }} aria-hidden />}
        {label}
      </span>
      <span className={styles.value}>
        <span className="num" data-testid="kpi-value">{value}</span>
        {unit && <span className={styles.unit}>{unit}</span>}
      </span>
    </div>
  )
}
