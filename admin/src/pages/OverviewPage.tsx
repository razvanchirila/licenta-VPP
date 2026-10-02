import { useQuery } from '@tanstack/react-query'
import { api } from '../api/endpoints'
import { Card } from '../components/Card'
import { CommunityMap } from '../components/CommunityMap'
import { KpiCard } from '../components/KpiCard'
import { PowerChart } from '../components/PowerChart'
import { PriceChart } from '../components/PriceChart'
import { TradesTable } from '../components/TradesTable'
import { useLive } from '../hooks/useLive'
import { dataSourceText, formatDate, formatNumber, formatPercent, hourOf, timeOf } from '../lib/format'
import type { VppToday } from '../types/api'
import styles from './OverviewPage.module.css'

function TodaySummary({ today }: { today?: VppToday }) {
  const rows: [string, string][] = today
    ? [
        ['Energie PV', `${formatNumber(today.pv_kwh, 1)} kWh`],
        ['Consum', `${formatNumber(today.load_kwh, 1)} kWh`],
        ['Import / export', `${formatNumber(today.import_kwh, 1)} / ${formatNumber(today.export_kwh, 1)} kWh`],
        ['Volum P2P', `${formatNumber(today.p2p_kwh, 2)} kWh`],
        ['Cost net rețea', `${formatNumber(today.cost_lei, 2)} lei`],
        ['Vârf import', `${formatNumber(today.peak_import_kw, 1)} kW`],
        ['Autoconsum', formatPercent(today.self_consumption)],
        ['Autonomie', formatPercent(today.self_sufficiency)],
        ['Tranzacții decontate', `${today.trades_settled} (${formatNumber(today.trades_value_lei, 2)} lei)`],
      ]
    : []
  return (
    <dl className={styles.summary}>
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd className="num">{value}</dd>
        </div>
      ))}
    </dl>
  )
}

export function OverviewPage() {
  const { status, day, last, trades } = useLive()
  const prices = useQuery({
    queryKey: ['prices', status?.sim_date],
    queryFn: api.prices,
    enabled: Boolean(status?.sim_date),
  })
  const stats = useQuery({ queryKey: ['vpp-stats'], queryFn: api.vppStats, refetchInterval: 10_000 })

  const c = last?.community
  const price = last?.price

  return (
    <div className={styles.page}>
      <div className={styles.kpis}>
        <KpiCard label="Producție PV" value={formatNumber(c?.pv_kw)} unit="kW" color="var(--series-pv)" />
        <KpiCard label="Consum" value={formatNumber(c?.load_kw)} unit="kW" color="var(--series-load)" />
        <KpiCard label="Import rețea" value={formatNumber(c?.import_kw)} unit="kW" color="var(--series-import)" />
        <KpiCard label="Export rețea" value={formatNumber(c?.export_kw)} unit="kW" color="var(--series-export)" />
        <KpiCard label="Schimb P2P" value={formatNumber(c?.p2p_kw)} unit="kW" color="var(--series-p2p)" />
        <KpiCard label="SOC mediu" value={formatNumber(c?.soc_percent, 1)} unit="%" hint={c ? `${formatNumber(c.soc_kwh, 1)} kWh în baterii` : undefined} />
        <KpiCard label="Preț import" value={formatNumber(price?.import, 3)} unit="lei/kWh" />
        <KpiCard label="Preț export" value={formatNumber(price?.export, 3)} unit="lei/kWh" />
        <KpiCard label="Preț P2P" value={formatNumber(price?.p2p, 3)} unit="lei/kWh" />
        <KpiCard label="Controller" value={status?.controller === 'mpc' ? 'MPC' : (status?.controller ?? '–')} />
        <KpiCard label="Sursa datelor" value={dataSourceText(status?.data_source, status?.data_year)} />
      </div>

      <div className={styles.grid}>
        <Card
          className={styles.wide}
          title="Puterea comunității"
          subtitle={`Ziua simulată ${formatDate(status?.sim_date)}, ultimul pas ${timeOf(last?.sim_datetime)}`}
        >
          <PowerChart day={day} />
        </Card>

        <Card title="Ziua simulată" subtitle="Totaluri de la 00:00">
          <TodaySummary today={stats.data?.today} />
        </Card>

        <Card
          className={styles.full}
          title="Harta comunității"
          subtitle="Starea fiecărei case la ultimul pas; clic pe o casă pentru detalii"
        >
          <CommunityMap step={last} />
        </Card>

        <Card className={styles.half} title="Prețuri azi" subtitle="lei/kWh, pe intervale de 15 minute">
          {prices.isError ? (
            <p className="muted">Prețurile nu au putut fi încărcate.</p>
          ) : (
            <PriceChart prices={prices.data} nowHour={last ? hourOf(last.sim_datetime) : null} height={400} />
          )}
        </Card>

        <Card className={styles.half} title="Tranzacții P2P recente" subtitle="Cele mai noi primele">
          <TradesTable trades={trades.slice(0, 10)} today={status?.sim_date} />
        </Card>
      </div>
    </div>
  )
}
