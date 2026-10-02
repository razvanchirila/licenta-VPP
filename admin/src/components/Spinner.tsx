import clsx from 'clsx'
import styles from './Spinner.module.css'

export function Spinner({ label, fullscreen = false }: { label?: string; fullscreen?: boolean }) {
  return (
    <div className={clsx(styles.wrap, fullscreen && styles.fullscreen)} role="status">
      <span className={styles.ring} aria-hidden />
      {label && <span className="muted">{label}</span>}
    </div>
  )
}
