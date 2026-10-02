import clsx from 'clsx'
import { formatDate, formatNumber, timeOf } from '../lib/format'
import type { Trade } from '../types/api'
import styles from './Table.module.css'

const houseName = (id: number) => `Casa ${id}`

function when(timestamp: string, today?: string): string {
  const time = timeOf(timestamp)
  return today && !timestamp.startsWith(today) ? `${formatDate(timestamp).slice(0, 5)} ${time}` : time
}

export function TradesTable({ trades, today }: { trades: Trade[]; today?: string }) {
  if (!trades.length) return <p className="muted">Nicio tranzacție P2P încă.</p>
  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Ora</th>
            <th>Vânzător</th>
            <th>Cumpărător</th>
            <th className={styles.right}>kWh</th>
            <th className={styles.right}>lei/kWh</th>
            <th className={styles.right}>Total lei</th>
            <th>Stare</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={`${t.sim_timestamp}-${t.seller_house_id}-${t.buyer_house_id}`} className={clsx(t.status === 'rejected' && styles.dim)}>
              <td className="num">{when(t.sim_timestamp, today)}</td>
              <td>{houseName(t.seller_house_id)}</td>
              <td>{houseName(t.buyer_house_id)}</td>
              <td className={clsx(styles.right, 'num')}>{formatNumber(t.energy_kwh, 3)}</td>
              <td className={clsx(styles.right, 'num')}>{formatNumber(t.price_lei_kwh, 3)}</td>
              <td className={clsx(styles.right, 'num')}>{formatNumber(t.total_value_lei, 3)}</td>
              <td>
                <span className={clsx(styles.pill, t.status === 'settled' ? styles.pillOk : styles.pillErr)}>
                  {t.status === 'settled' ? 'decontată' : 'respinsă'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
