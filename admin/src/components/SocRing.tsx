import { socColor } from '../lib/community'

interface SocRingProps {
  percent: number | null
  size?: number
  stroke?: number
}

export function SocRing({ percent, size = 56, stroke = 5 }: SocRingProps) {
  const r = (size - stroke) / 2
  const circumference = 2 * Math.PI * r
  const value = percent === null ? 0 : Math.max(0, Math.min(100, percent))
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label={percent === null ? 'fără baterie' : `SOC ${Math.round(value)} %`}
    >
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--surface-3)" strokeWidth={stroke} />
      {percent !== null && (
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={socColor(value)}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${(value / 100) * circumference} ${circumference}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
      )}
      <text
        x="50%"
        y="50%"
        dominantBaseline="central"
        textAnchor="middle"
        fill={percent === null ? 'var(--text-3)' : 'var(--text)'}
        fontSize={size * 0.24}
        fontWeight={600}
      >
        {percent === null ? 'fără' : `${Math.round(value)}%`}
      </text>
    </svg>
  )
}
