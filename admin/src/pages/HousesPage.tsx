import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { Outlet, useNavigate, useParams } from 'react-router'
import { api } from '../api/endpoints'
import { Card } from '../components/Card'
import { Spinner } from '../components/Spinner'
import tableStyles from '../components/Table.module.css'
import { useLive } from '../hooks/useLive'
import { formatNumber, formatSigned } from '../lib/format'
import type { House, HouseStep } from '../types/api'

interface Row {
  house: House
  step: HouseStep | null
}

export function HousesPage() {
  const navigate = useNavigate()
  const { houseId } = useParams()
  const { last } = useLive()
  const houses = useQuery({ queryKey: ['houses'], queryFn: api.houses, refetchInterval: 10_000 })

  const liveById = new Map((last?.houses ?? []).map((h) => [h.id, h]))
  const rows: Row[] = (houses.data ?? []).map((house) => ({ house, step: liveById.get(house.id) ?? house.last_step }))
  const open = (id: number) => navigate(`/case/${id}`)

  return (
    <>
      <Card
        title="Case"
        subtitle="Valori la ultimul pas simulat. Puteri în kW; P2P pozitiv = cumpără, negativ = vinde. Clic pe un rând pentru detalii."
      >
        {houses.isPending ? (
          <Spinner label="Se încarcă casele…" />
        ) : houses.isError ? (
          <p className="muted">{houses.error.message}</p>
        ) : (
          <div className={tableStyles.wrap}>
            <table className={tableStyles.table}>
              <thead>
                <tr>
                  <th>Casa</th>
                  <th>Utilizator</th>
                  <th>Mod</th>
                  <th className={tableStyles.right}>SOC</th>
                  <th className={tableStyles.right}>PV</th>
                  <th className={tableStyles.right}>Consum</th>
                  <th className={tableStyles.right}>Import</th>
                  <th className={tableStyles.right}>Export</th>
                  <th className={tableStyles.right}>P2P</th>
                  <th className={tableStyles.right}>Sold</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(({ house, step }) => {
                  const p2p = step ? step.p2p_in_kw - step.p2p_out_kw : null
                  return (
                    <tr
                      key={house.id}
                      tabIndex={0}
                      className={clsx(tableStyles.clickable, String(house.id) === houseId && tableStyles.selected)}
                      onClick={() => open(house.id)}
                      onKeyDown={(e) => e.key === 'Enter' && open(house.id)}
                    >
                      <td>
                        <strong>{house.name}</strong>
                      </td>
                      <td className="muted">{house.user ?? '–'}</td>
                      <td>{step?.mode ?? house.mode}</td>
                      <td className={clsx(tableStyles.right, 'num')}>
                        {house.has_battery ? `${formatNumber(step?.soc_percent ?? house.battery?.soc_percent, 1)} %` : 'fără baterie'}
                      </td>
                      <td className={clsx(tableStyles.right, 'num')}>{formatNumber(step?.pv_kw)}</td>
                      <td className={clsx(tableStyles.right, 'num')}>{formatNumber(step?.load_kw)}</td>
                      <td className={clsx(tableStyles.right, 'num')}>{formatNumber(step?.imp_kw)}</td>
                      <td className={clsx(tableStyles.right, 'num')}>{formatNumber(step?.exp_kw)}</td>
                      <td
                        className={clsx(
                          tableStyles.right,
                          'num',
                          p2p !== null && p2p > 0.005 && tableStyles.pos,
                          p2p !== null && p2p < -0.005 && tableStyles.neg,
                        )}
                      >
                        {formatSigned(p2p)}
                      </td>
                      <td className={clsx(tableStyles.right, 'num')}>{formatNumber(house.wallet_balance_lei)} lei</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <Outlet />
    </>
  )
}
