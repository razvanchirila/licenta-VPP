import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router'
import { ApiError } from '../api/client'
import { api } from '../api/endpoints'
import { useLive } from '../hooks/useLive'
import { useToast } from '../hooks/useToast'
import { batteryModules } from '../lib/community'
import { formatNumber, formatSigned, scheduleText } from '../lib/format'
import type { Device, House, HouseMode, HouseStep, Wallet } from '../types/api'
import styles from './HouseDrawer.module.css'
import { SocRing } from './SocRing'
import { Spinner } from './Spinner'

const MODES: HouseMode[] = ['Eco', 'Profit']

function Stat({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className={styles.stat}>
      <span>{label}</span>
      <strong className="num">
        {value}
        {unit && <small> {unit}</small>}
      </strong>
    </div>
  )
}

function LiveStats({ step }: { step: HouseStep | null }) {
  return (
    <div className={styles.stats}>
      <Stat label="PV" value={formatNumber(step?.pv_kw)} unit="kW" />
      <Stat label="Consum" value={formatNumber(step?.load_kw)} unit="kW" />
      <Stat label="Import" value={formatNumber(step?.imp_kw)} unit="kW" />
      <Stat label="Export" value={formatNumber(step?.exp_kw)} unit="kW" />
      <Stat label="P2P (+ cumpără)" value={formatSigned(step ? step.p2p_in_kw - step.p2p_out_kw : null)} unit="kW" />
      <Stat label="Baterie (+ încarcă)" value={formatSigned(step ? step.ch_kw - step.dis_kw : null)} unit="kW" />
    </div>
  )
}

function BatterySection({ house, step }: { house: House; step: HouseStep | null }) {
  const b = house.battery
  if (!b) return <p className="muted">Casa nu are baterie.</p>
  const modules = batteryModules(b.capacity_kwh)
  return (
    <div className={styles.battery}>
      <SocRing percent={step?.soc_percent ?? b.soc_percent} size={92} stroke={8} />
      <dl className={styles.kv}>
        <dt>Module</dt>
        <dd>
          {modules} × 16 kWh
        </dd>
        <dt>Capacitate</dt>
        <dd className="num">{formatNumber(b.capacity_kwh, 1)} kWh</dd>
        <dt>Energie stocată</dt>
        <dd className="num">{formatNumber(step?.soc_kwh ?? b.soc_kwh, 2)} kWh</dd>
        <dt>SOC minim</dt>
        <dd className="num">{formatNumber(b.soc_min_kwh, 1)} kWh</dd>
        <dt>Putere încărcare / descărcare</dt>
        <dd className="num">
          {formatNumber(b.p_ch_max_kw, 0)} / {formatNumber(b.p_dis_max_kw, 0)} kW
        </dd>
        <dt>Rezervă VPP</dt>
        <dd className="num">{formatNumber(b.vpp_reserve_kwh, 2)} kWh</dd>
      </dl>
    </div>
  )
}

function WalletSection({ house, wallet }: { house: House; wallet?: Wallet }) {
  const prefs = house.trading
  return (
    <dl className={styles.kv}>
      <dt>Sold</dt>
      <dd className="num">
        <strong>{formatNumber(wallet?.balance_lei ?? house.wallet_balance_lei)} lei</strong>
      </dd>
      <dt>Câștigat / cheltuit</dt>
      <dd className="num">
        {formatNumber(wallet?.total_earned_lei)} / {formatNumber(wallet?.total_spent_lei)} lei
      </dd>
      <dt>Tranzacții în portofel</dt>
      <dd className="num">{wallet?.transaction_count ?? '–'}</dd>
      <dt>Schimb P2P</dt>
      <dd>
        {prefs
          ? `vânzare ${prefs.selling_enabled ? 'da' : 'nu'}, cumpărare ${prefs.buying_enabled ? 'da' : 'nu'}`
          : '–'}
      </dd>
    </dl>
  )
}

interface DeviceRowProps {
  device: Device
  busy: boolean
  onToggle: (device: Device) => void
}

function DeviceRow({ device, busy, onToggle }: DeviceRowProps) {
  const locked = device.critical && device.status_on
  return (
    <li className={styles.device}>
      <div className={styles.deviceMain}>
        <span className={styles.deviceName}>
          {device.name}
          {device.critical && <span className={styles.tag}>critic</span>}
        </span>
        <span className={styles.deviceMeta}>
          {scheduleText(device.schedule)} · {formatNumber(device.power_w, 0)} W
        </span>
      </div>
      <div className={styles.deviceDraw}>
        <strong className={clsx('num', device.current_power_kw > 0 && styles.drawing)}>
          {formatNumber(device.current_power_kw, 2)} kW
        </strong>
        <span className="num">{formatNumber(device.accumulated_energy_kwh, 2)} kWh</span>
      </div>
      <span title={locked ? 'Dispozitiv critic: nu poate fi oprit' : undefined}>
        <button
          type="button"
          role="switch"
          aria-checked={device.status_on}
          aria-label={`${device.name}: ${device.status_on ? 'pornit' : 'oprit'}`}
          className={clsx(styles.switch, device.status_on && styles.on)}
          disabled={locked || busy}
          onClick={() => onToggle(device)}
        >
          <span />
        </button>
      </span>
    </li>
  )
}

export function HouseDrawer() {
  const { houseId } = useParams()
  const id = Number(houseId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()
  const { last } = useLive()
  const closeRef = useRef<HTMLButtonElement>(null)

  const validId = Number.isInteger(id) && id > 0
  const house = useQuery({ queryKey: ['house', id], queryFn: () => api.house(id), enabled: validId })
  const wallet = useQuery({ queryKey: ['wallet', id], queryFn: () => api.wallet(id), enabled: validId })
  const missing = !validId || (house.error instanceof ApiError && house.error.status === 404)

  const stepNumber = last?.step
  useEffect(() => {
    if (stepNumber === undefined) return
    void queryClient.invalidateQueries({ queryKey: ['house', id] })
    void queryClient.invalidateQueries({ queryKey: ['wallet', id] })
  }, [stepNumber, id, queryClient])

  const close = () => navigate('/case')
  useEffect(() => {
    closeRef.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && navigate('/case')
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [navigate])

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['house', id] })
    void queryClient.invalidateQueries({ queryKey: ['houses'] })
  }
  const setMode = useMutation({
    mutationFn: (mode: HouseMode) => api.setMode(id, mode),
    onSuccess: (res) => {
      toast(res.message, 'ok')
      refresh()
    },
    onError: (e) => toast(e.message, 'error'),
  })
  const toggle = useMutation({
    mutationFn: (device: Device) => api.toggleDevice(id, device.id),
    onSuccess: (d) => {
      toast(`${d.name}: ${d.status_on ? 'pornit' : 'oprit'}`, 'ok')
      refresh()
    },
    onError: (e) => toast(e.message, 'error'),
  })

  const data = house.data
  const step = last?.houses.find((h) => h.id === id) ?? data?.last_step ?? null

  return (
    <div className={styles.overlay} onClick={close}>
      <aside
        className={styles.drawer}
        role="dialog"
        aria-modal="true"
        aria-label={data?.name ?? 'Casa'}
        onClick={(e) => e.stopPropagation()}
      >
        <header className={styles.head}>
          <div>
            <h2>{data?.name ?? (validId ? `Casa ${id}` : 'Casa')}</h2>
            <p className="muted">
              {data
                ? `${data.user ? `utilizator ${data.user}` : 'fără utilizator'} · PV ${formatNumber(data.pv_capacity_kw, 0)} kW`
                : ' '}
            </p>
          </div>
          <button ref={closeRef} type="button" className="btn btn-ghost" onClick={close} aria-label="Închide">
            ✕
          </button>
        </header>

        {missing ? (
          <div className={styles.missing}>
            <p>Casa nu există.</p>
            <button type="button" className="btn" onClick={close}>
              Înapoi la case
            </button>
          </div>
        ) : house.isPending ? (
          <Spinner label="Se încarcă…" />
        ) : house.isError || !data ? (
          <p className={styles.missing}>{house.error?.message ?? 'Casa nu a putut fi încărcată.'}</p>
        ) : (
          <div className={styles.body}>
            <section>
              <h3>Mod de funcționare</h3>
              <div className="segmented" role="group" aria-label="Mod de funcționare">
                {MODES.map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    aria-pressed={data.mode === mode}
                    disabled={setMode.isPending}
                    onClick={() => data.mode !== mode && setMode.mutate(mode)}
                  >
                    {mode}
                  </button>
                ))}
              </div>
              <p className={styles.hint}>
                Profit renunță la mai mult consum flexibil când prețul e mare și încarcă bateria din rețea când e mic.
                Modul contează doar pentru controllerul pe reguli.
              </p>
            </section>

            <section>
              <h3>Acum</h3>
              <LiveStats step={step} />
            </section>

            <section>
              <h3>Baterie</h3>
              <BatterySection house={data} step={step} />
            </section>

            <section>
              <h3>Portofel</h3>
              <WalletSection house={data} wallet={wallet.data} />
            </section>

            <section>
              <h3>
                Dispozitive <span className="muted">({data.device_count})</span>
              </h3>
              {data.devices.length ? (
                <ul className={styles.devices}>
                  {data.devices.map((d) => (
                    <DeviceRow
                      key={d.id}
                      device={d}
                      busy={toggle.isPending && toggle.variables?.id === d.id}
                      onToggle={(device) => toggle.mutate(device)}
                    />
                  ))}
                </ul>
              ) : (
                <p className="muted">Niciun dispozitiv.</p>
              )}
            </section>
          </div>
        )}
      </aside>
    </div>
  )
}
