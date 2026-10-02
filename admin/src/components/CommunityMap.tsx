import clsx from 'clsx'
import { useNavigate } from 'react-router'
import { netExchangeKw, p2pFlows, type Flow } from '../lib/community'
import { formatNumber, formatSigned } from '../lib/format'
import type { HouseStep, StepResult } from '../types/api'
import styles from './CommunityMap.module.css'
import { SocRing } from './SocRing'

const COLS = 5
const ROWS = 2
const CARD_W = 156
const CARD_H = 168
const STEP_X = 200
const CORRIDOR = 96
const STEP_Y = CARD_H + CORRIDOR
const PAD_X = 22
const PAD_Y = 8
const WIDTH = PAD_X * 2 + STEP_X * (COLS - 1) + CARD_W
const HEIGHT = PAD_Y * 2 + STEP_Y * (ROWS - 1) + CARD_H
const BUS_Y = PAD_Y + CARD_H + CORRIDOR / 2

interface Point {
  x: number
  y: number
}

function origin(index: number): Point {
  return { x: PAD_X + (index % COLS) * STEP_X, y: PAD_Y + Math.floor(index / COLS) * STEP_Y }
}

interface RoutedFlow extends Flow {
  path: string
}

// P2P energy goes over the community's internal line, so every flow is drawn through the corridor
// between the two rows: out of the seller's edge facing the corridor, along it, into the buyer.
function routeFlows(flows: Flow[], indexById: Map<number, number>): RoutedFlow[] {
  const valid = flows.filter((f) => indexById.has(f.from) && indexById.has(f.to))
  const ports = new Map<number, Flow[]>()
  for (const f of valid) for (const id of [f.from, f.to]) ports.set(id, [...(ports.get(id) ?? []), f])

  const portOf = (houseId: number, flow: Flow): Point => {
    const o = origin(indexById.get(houseId)!)
    const list = ports.get(houseId)!
    const x = o.x + (CARD_W * (list.indexOf(flow) + 1)) / (list.length + 1)
    return { x, y: o.y < BUS_Y ? o.y + CARD_H : o.y }
  }

  const laneGap = Math.min(10, (CORRIDOR - 24) / Math.max(1, valid.length))
  return valid.map((f, i) => {
    const a = portOf(f.from, f)
    const b = portOf(f.to, f)
    const lane = BUS_Y + (i - (valid.length - 1) / 2) * laneGap
    // the arrowhead needs a few units of room before the card edge
    const endY = b.y + (b.y > lane ? -4 : 4)
    return { ...f, path: `M${a.x},${a.y} V${lane} H${b.x} V${endY}` }
  })
}

interface HouseNodeProps {
  house: HouseStep
  index: number
  onOpen: (id: number) => void
}

function HouseNode({ house, index, onOpen }: HouseNodeProps) {
  const o = origin(index)
  const net = netExchangeKw(house)
  const giving = net > 0.005
  const taking = net < -0.005
  return (
    <g
      transform={`translate(${o.x} ${o.y})`}
      className={styles.node}
      role="link"
      tabIndex={0}
      aria-label={`${house.name}, deschide detaliile`}
      onClick={() => onOpen(house.id)}
      onKeyDown={(e) => e.key === 'Enter' && onOpen(house.id)}
    >
      <rect width={CARD_W} height={CARD_H} rx={14} className={clsx(styles.card, giving && styles.giving)} />
      <text x={14} y={26} className={styles.name}>
        {house.name}
      </text>
      <text x={CARD_W - 14} y={26} textAnchor="end" className={clsx(styles.mode, house.mode === 'Profit' && styles.profit)}>
        {house.mode}
      </text>
      <g transform="translate(12 40)">
        <SocRing percent={house.soc_percent} size={62} stroke={6} />
      </g>
      <text x={88} y={66} className={clsx(styles.net, giving && styles.pos, taking && styles.neg)}>
        {formatSigned(net, 1)}
      </text>
      <text x={88} y={86} className={styles.small}>
        kW schimb net
      </text>
      <line x1={14} x2={CARD_W - 14} y1={116} y2={116} className={styles.divider} />
      <text x={14} y={137} className={styles.small}>
        <tspan className={styles.pvDot}>●</tspan> PV {formatNumber(house.pv_kw, 2)} kW
      </text>
      <text x={14} y={156} className={styles.small}>
        <tspan className={styles.loadDot}>●</tspan> Consum {formatNumber(house.load_kw, 2)} kW
      </text>
    </g>
  )
}

export function CommunityMap({ step }: { step: StepResult | null }) {
  const navigate = useNavigate()
  if (!step) return <p className="muted">Se așteaptă primul pas al simulării…</p>

  const houses = [...step.houses].sort((x, y) => x.id - y.id).slice(0, COLS * ROWS)
  const indexById = new Map(houses.map((h, i) => [h.id, i]))
  const names = new Map(houses.map((h) => [h.id, h.name]))
  const flows = routeFlows(p2pFlows(step.trades), indexById)
  const maxKwh = Math.max(1e-9, ...flows.map((f) => f.kwh))

  return (
    <div className={styles.wrap}>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className={styles.svg} role="group" aria-label="Harta comunității">
        <defs>
          <marker id="p2p-arrow" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4" markerHeight="4" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill="var(--series-p2p)" />
          </marker>
        </defs>
        <line x1={PAD_X} x2={WIDTH - PAD_X} y1={BUS_Y} y2={BUS_Y} className={styles.bus} />
        <text x={PAD_X} y={BUS_Y - 8} className={styles.busLabel}>
          linia internă a comunității
        </text>
        {houses.map((h, i) => (
          <HouseNode key={h.id} house={h} index={i} onOpen={(id) => navigate(`/case/${id}`)} />
        ))}
        {flows.map((f) => (
          <path
            key={`${f.from}-${f.to}`}
            d={f.path}
            className={styles.flow}
            data-testid="p2p-flow"
            strokeWidth={2 + 3 * (f.kwh / maxKwh)}
            markerEnd="url(#p2p-arrow)"
          >
            <title>{`${names.get(f.from)} → ${names.get(f.to)}: ${formatNumber(f.kwh, 3)} kWh`}</title>
          </path>
        ))}
      </svg>
      <div className={styles.legend}>
        <span>
          <i className={styles.legendFlow} /> schimb P2P în ultimul pas: {flows.length}
        </span>
        <span>inelul arată nivelul bateriei (SOC)</span>
        <span>
          schimb net: <b className={styles.pos}>+</b> casa dă energie, <b className={styles.neg}>−</b> casa primește
        </span>
      </div>
    </div>
  )
}
