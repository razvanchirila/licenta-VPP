import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { api } from '../api/endpoints'
import { Card } from '../components/Card'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { Spinner } from '../components/Spinner'
import { useLive } from '../hooks/useLive'
import { useToast } from '../hooks/useToast'
import { dataSourceText, formatDate, formatNumber } from '../lib/format'
import { simStateLabel } from '../lib/simState'
import type { Controller, EditableConfig, SimConfig, SimStatus } from '../types/api'
import styles from './SimulationPage.module.css'

const TICK_MIN = 0.2
const TICK_MAX = 60
const SPEED_PRESETS = [0.5, 1, 2, 5]

type NumericField = Exclude<keyof EditableConfig, 'controller' | 'tick_seconds'>

const CONFIG_FIELDS: { key: NumericField; label: string; min: number; max?: number; step: number }[] = [
  { key: 'import_max_kw', label: 'Import maxim din rețea (kW)', min: 0, step: 1 },
  { key: 'export_max_kw', label: 'Export maxim în rețea (kW)', min: 0, step: 1 },
  { key: 'internal_line_kw', label: 'Limita liniei interne (kW)', min: 0, step: 1 },
  { key: 'p2p_price_factor', label: 'Preț P2P (× preț import)', min: 0.01, max: 1, step: 0.01 },
  { key: 'min_p2p_balance_lei', label: 'Sold minim pentru P2P (lei)', min: 0, step: 1 },
  { key: 'seed', label: 'Seed scenariu', min: 0, step: 1 },
]

function StatusList({ status }: { status: SimStatus | null }) {
  if (!status) return <Spinner />
  const rows: [string, string][] = [
    ['Ziua și ora simulată', `${formatDate(status.sim_date)} ${status.sim_time}`],
    ['Controller', status.controller === 'mpc' ? 'MPC (optimizare 24 h)' : 'reguli'],
    ['Date', dataSourceText(status.data_source, status.data_year)],
    ['Pas simulat', `${Math.round(status.dt_hours * 60)} min la ${formatNumber(status.tick_seconds, 1)} s reale`],
    ['Pasul zilei', `${status.step_of_day} / ${status.steps_per_day}`],
    ['Pași totali', String(status.total_steps)],
    ['Case', String(status.n_houses)],
    ['Clienți conectați live', String(status.websocket_clients)],
  ]
  return (
    <dl className={styles.kv}>
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd className="num">{value}</dd>
        </div>
      ))}
    </dl>
  )
}

function SpeedControl({ current, onApply, busy }: { current: number; onApply: (v: number) => void; busy: boolean }) {
  const [value, setValue] = useState(String(current))
  const parsed = Number(value)
  const valid = Number.isFinite(parsed) && parsed >= TICK_MIN && parsed <= TICK_MAX

  return (
    <form
      className={styles.speed}
      onSubmit={(e) => {
        e.preventDefault()
        if (valid) onApply(parsed)
      }}
    >
      <label htmlFor="tick">Secunde reale per pas</label>
      <div className={styles.speedRow}>
        <input
          id="tick"
          className="input"
          type="number"
          min={TICK_MIN}
          max={TICK_MAX}
          step={0.1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          aria-invalid={!valid}
        />
        <button type="submit" className="btn" disabled={!valid || busy || parsed === current}>
          Aplică
        </button>
      </div>
      <div className={styles.presets}>
        {SPEED_PRESETS.map((p) => (
          <button key={p} type="button" className="btn" disabled={busy || p === current} onClick={() => onApply(p)}>
            {formatNumber(p, p < 1 ? 1 : 0)} s
          </button>
        ))}
      </div>
    </form>
  )
}

function ConfigForm({ config, onSave, onReset, busy }: {
  config: SimConfig
  onSave: (changes: Partial<EditableConfig>) => void
  onReset: () => void
  busy: boolean
}) {
  const [values, setValues] = useState<Record<NumericField, string>>(() => {
    const entries = CONFIG_FIELDS.map((f) => [f.key, String(config[f.key])])
    return Object.fromEntries(entries) as Record<NumericField, string>
  })

  const changes: Partial<EditableConfig> = {}
  let invalid = false
  for (const f of CONFIG_FIELDS) {
    const v = Number(values[f.key])
    if (values[f.key] === '' || !Number.isFinite(v)) invalid = true
    else if (v !== config[f.key]) changes[f.key] = v
  }
  const dirty = Object.keys(changes).length > 0

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (dirty && !invalid) onSave(changes)
  }

  return (
    <form className={styles.config} onSubmit={submit}>
      <div className={styles.configGrid}>
        {CONFIG_FIELDS.map((f) => (
          <label key={f.key} className={styles.field}>
            <span>{f.label}</span>
            <input
              className="input"
              type="number"
              min={f.min}
              max={f.max}
              step={f.step}
              value={values[f.key]}
              onChange={(e) => setValues((prev) => ({ ...prev, [f.key]: e.target.value }))}
            />
          </label>
        ))}
        <div className={styles.field}>
          <span>Pas simulat</span>
          <output className={styles.readonly}>{Math.round(config.dt_hours * 60)} min</output>
        </div>
        <div className={styles.field}>
          <span>Sursa datelor (din .env)</span>
          <output className={styles.readonly}>{dataSourceText(config.data_source, config.data_year)}</output>
        </div>
      </div>
      <div className={styles.configActions}>
        <button type="submit" className="btn btn-primary" disabled={!dirty || invalid || busy}>
          Salvează
        </button>
        <button type="button" className="btn" disabled={busy} onClick={onReset}>
          Valori implicite
        </button>
        <span className="muted">Modificările se aplică de la pasul următor.</span>
      </div>
    </form>
  )
}

export function SimulationPage() {
  const { status, dispatch } = useLive()
  const queryClient = useQueryClient()
  const toast = useToast()
  const [confirmReset, setConfirmReset] = useState(false)
  const config = useQuery({ queryKey: ['config'], queryFn: api.config })

  const refreshStatus = () => api.status().then((s) => dispatch({ type: 'status', status: s }))
  const onError = (e: Error) => toast(e.message, 'error')

  const action = useMutation({
    mutationFn: api.simAction,
    onSuccess: (res, name) => {
      dispatch({ type: 'status', status: res.status })
      if (name === 'reset') {
        dispatch({ type: 'reset' })
        void queryClient.invalidateQueries()
      }
      toast(res.message, 'ok')
    },
    onError,
  })

  const step = useMutation({
    mutationFn: api.step,
    onSuccess: async (result) => {
      dispatch({ type: 'step', step: result })
      await refreshStatus()
      toast('Un pas simulat', 'ok')
    },
    onError,
  })

  const afterConfig = (res: { message: string; config: SimConfig }) => {
    queryClient.setQueryData(['config'], res.config)
    toast(res.message, 'ok')
    void refreshStatus()
  }
  const speed = useMutation({
    mutationFn: api.speed,
    onSuccess: (res) => {
      toast(res.message, 'ok')
      void queryClient.invalidateQueries({ queryKey: ['config'] })
      void refreshStatus()
    },
    onError,
  })
  const save = useMutation({ mutationFn: api.updateConfig, onSuccess: afterConfig, onError })
  const reset = useMutation({ mutationFn: api.resetConfig, onSuccess: afterConfig, onError })

  const running = Boolean(status?.running)
  const paused = Boolean(status?.paused)
  const busy = action.isPending || step.isPending
  const sim = simStateLabel(status)
  const controller = config.data?.controller ?? status?.controller

  return (
    <div className={styles.page}>
      <Card
        title="Starea simulării"
        subtitle={`Stare: ${sim.label}`}
        actions={
          <>
            <button type="button" className="btn btn-primary" disabled={busy || running} onClick={() => action.mutate('start')}>
              Pornește
            </button>
            <button type="button" className="btn" disabled={busy || !running} onClick={() => action.mutate('stop')}>
              Oprește
            </button>
            <button type="button" className="btn" disabled={busy || !running || paused} onClick={() => action.mutate('pause')}>
              Pauză
            </button>
            <button type="button" className="btn" disabled={busy || !running || !paused} onClick={() => action.mutate('resume')}>
              Reia
            </button>
            <button type="button" className="btn" disabled={busy} onClick={() => step.mutate()}>
              Un pas
            </button>
            <button type="button" className="btn btn-danger" disabled={busy} onClick={() => setConfirmReset(true)}>
              Reset
            </button>
          </>
        }
      >
        <StatusList status={status} />
      </Card>

      <div className={styles.row}>
        <Card title="Viteză" subtitle="Cât durează în realitate un pas de 15 minute simulate">
          {status ? (
            <SpeedControl
              key={status.tick_seconds}
              current={status.tick_seconds}
              busy={speed.isPending}
              onApply={(v) => speed.mutate(v)}
            />
          ) : (
            <Spinner />
          )}
        </Card>

        <Card title="Controller" subtitle="Strategia care decide bateriile, schimbul P2P și rețeaua">
          <div className="segmented" role="group" aria-label="Controller">
            {(['reguli', 'mpc'] as Controller[]).map((c) => (
              <button
                key={c}
                type="button"
                aria-pressed={controller === c}
                disabled={save.isPending}
                onClick={() => controller !== c && save.mutate({ controller: c })}
              >
                {c === 'mpc' ? 'MPC' : 'Reguli'}
              </button>
            ))}
          </div>
          <p className={styles.hint}>
            Reguli: priorități fixe la fiecare pas. MPC: optimizare liniară pe următoarele 24 de ore, reluată la fiecare
            pas.
          </p>
        </Card>
      </div>

      <Card title="Configurație" subtitle="Limitele rețelei și ale schimbului P2P">
        {config.data ? (
          <ConfigForm
            key={JSON.stringify(config.data)}
            config={config.data}
            busy={save.isPending || reset.isPending}
            onSave={(changes) => save.mutate(changes)}
            onReset={() => reset.mutate()}
          />
        ) : config.isError ? (
          <p className="muted">{config.error.message}</p>
        ) : (
          <Spinner />
        )}
      </Card>

      <ConfirmDialog
        open={confirmReset}
        title="Resetezi simularea?"
        message="Se șterg pașii, tranzacțiile și jurnalele de energie; bateriile revin la 50 %, portofelele la soldul inițial, iar ceasul la data de start."
        confirmLabel="Resetează"
        onCancel={() => setConfirmReset(false)}
        onConfirm={() => {
          setConfirmReset(false)
          action.mutate('reset')
        }}
      />
    </div>
  )
}
