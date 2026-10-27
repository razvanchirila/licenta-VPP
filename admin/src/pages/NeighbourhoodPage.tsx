import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { useState } from 'react'
import { api } from '../api/endpoints'
import { Card } from '../components/Card'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { Spinner } from '../components/Spinner'
import { useToast } from '../hooks/useToast'
import { heatingLabel, insulationLabel, sameSpec, toggleDevice } from '../lib/neighbourhood'
import type { HouseSpec, Neighbourhood } from '../types/api'
import styles from './NeighbourhoodPage.module.css'

const PEOPLE = [1, 2, 3, 4, 5, 6, 7, 8]

interface HouseEditorProps {
  saved: HouseSpec
  catalog: Neighbourhood['catalog']
}

function HouseEditor({ saved, catalog }: HouseEditorProps) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [draft, setDraft] = useState(saved)
  const [base, setBase] = useState(saved)
  if (base !== saved) {
    // the server copy changed (saved here, or reset): start again from it
    setBase(saved)
    setDraft(saved)
  }
  const dirty = !sameSpec(draft, saved)
  const save = useMutation({
    mutationFn: () => api.saveHouseSpec(draft),
    onSuccess: () => {
      toast(`Casa ${saved.id} salvată; simularea o folosește de la pasul următor`, 'ok')
      void queryClient.invalidateQueries({ queryKey: ['neighbourhood'] })
      void queryClient.invalidateQueries({ queryKey: ['houses'] })
    },
    onError: (error) => toast(error.message, 'error'),
  })
  const set = <K extends keyof HouseSpec>(key: K, value: HouseSpec[K]) => setDraft({ ...draft, [key]: value })

  return (
    <article className={clsx(styles.house, dirty && styles.dirty)} aria-label={`Casa ${saved.id}`}>
      <div className={styles.head}>
        <strong>Casa {saved.id}</strong>
        <input
          className="input"
          aria-label="Descriere"
          value={draft.description}
          maxLength={200}
          onChange={(e) => set('description', e.target.value)}
        />
      </div>
      <div className={styles.fields}>
        <label className={styles.field}>
          Persoane
          <select className="input" value={draft.people} onChange={(e) => set('people', Number(e.target.value))}>
            {PEOPLE.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          Încălzire
          <select className="input" value={draft.heating} onChange={(e) => set('heating', e.target.value)}>
            {catalog.heating.map((h) => (
              <option key={h} value={h}>
                {heatingLabel(h)}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          Izolație
          <select className="input" value={draft.insulation} onChange={(e) => set('insulation', e.target.value)}>
            {catalog.insulation.map((i) => (
              <option key={i} value={i}>
                {insulationLabel(i)}
              </option>
            ))}
          </select>
        </label>
        <div className={styles.field}>
          Ziua
          <label className={styles.check}>
            <input
              type="checkbox"
              checked={draft.home_daytime}
              onChange={(e) => set('home_daytime', e.target.checked)}
            />
            e cineva acasă
          </label>
        </div>
      </div>
      <div className={styles.chips} role="group" aria-label="Dispozitive opționale">
        {catalog.optional.map((name) => (
          <button
            key={name}
            type="button"
            className={styles.chip}
            aria-pressed={draft.devices.includes(name)}
            onClick={() => setDraft(toggleDevice(draft, name, catalog.optional))}
          >
            {name}
          </button>
        ))}
      </div>
      <div className={styles.footer}>
        <button type="button" className="btn btn-ghost" disabled={!dirty || save.isPending} onClick={() => setDraft(saved)}>
          Anulează
        </button>
        <button type="button" className="btn btn-primary" disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
          {save.isPending ? 'Se salvează…' : 'Salvează'}
        </button>
      </div>
    </article>
  )
}

export function NeighbourhoodPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [confirmReset, setConfirmReset] = useState(false)
  const data = useQuery({ queryKey: ['neighbourhood'], queryFn: api.neighbourhood })
  const reset = useMutation({
    mutationFn: api.resetNeighbourhood,
    onSuccess: () => {
      toast('Cartierul a revenit la case.csv', 'ok')
      void queryClient.invalidateQueries({ queryKey: ['neighbourhood'] })
      void queryClient.invalidateQueries({ queryKey: ['houses'] })
    },
    onError: (error) => toast(error.message, 'error'),
  })
  const download = async () => {
    try {
      const text = await api.exportNeighbourhood()
      const url = URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' }))
      const link = Object.assign(document.createElement('a'), { href: url, download: 'case.csv' })
      link.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      toast((error as Error).message, 'error')
    }
  }

  return (
    <Card
      title="Cartier"
      subtitle={
        <>
          Cine locuiește în fiecare casă și ce dispozitive are. Rezultatele din lucrare folosesc{' '}
          <code>backend/data/case.csv</code>; aici se schimbă doar simularea live.
          {data.data && <span className={styles.always}> Toate casele au: {data.data.catalog.always.join(', ')}.</span>}
        </>
      }
      actions={
        <>
          <button type="button" className="btn" onClick={() => void download()}>
            Exportă CSV
          </button>
          <button type="button" className="btn btn-danger" disabled={reset.isPending} onClick={() => setConfirmReset(true)}>
            Revino la case.csv
          </button>
        </>
      }
    >
      {data.isPending ? (
        <Spinner label="Se încarcă cartierul…" />
      ) : data.isError ? (
        <p className="muted">{data.error.message}</p>
      ) : (
        <div className={styles.grid}>
          {data.data.houses.map((house) => (
            <HouseEditor key={house.id} saved={house} catalog={data.data.catalog} />
          ))}
        </div>
      )}
      <ConfirmDialog
        open={confirmReset}
        title="Revii la case.csv?"
        message="Toate casele primesc din nou persoanele, încălzirea și dispozitivele din fișier. Dispozitivele adăugate de mână rămân."
        confirmLabel="Revino"
        onConfirm={() => {
          setConfirmReset(false)
          reset.mutate()
        }}
        onCancel={() => setConfirmReset(false)}
      />
    </Card>
  )
}
