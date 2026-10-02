import clsx from 'clsx'
import type { ReactNode } from 'react'
import styles from './Card.module.css'

interface CardProps {
  title?: string
  subtitle?: ReactNode
  actions?: ReactNode
  className?: string
  children: ReactNode
}

export function Card({ title, subtitle, actions, className, children }: CardProps) {
  return (
    <section className={clsx(styles.card, className)}>
      {(title || actions) && (
        <header className={styles.head}>
          <div>
            {title && <h2 className={styles.title}>{title}</h2>}
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </div>
          {actions && <div className={styles.actions}>{actions}</div>}
        </header>
      )}
      {children}
    </section>
  )
}
