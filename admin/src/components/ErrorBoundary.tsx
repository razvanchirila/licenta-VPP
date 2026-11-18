import { Component, type ReactNode } from 'react'
import styles from './ErrorBoundary.module.css'

interface ErrorBoundaryProps {
  /** when it changes (another page), the boundary tries to render its children again */
  resetKey?: string
  children: ReactNode
}

interface ErrorBoundaryState {
  failed: boolean
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { failed: false }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { failed: true }
  }

  componentDidUpdate(prev: ErrorBoundaryProps) {
    if (this.state.failed && prev.resetKey !== this.props.resetKey) this.setState({ failed: false })
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div className={styles.box} role="alert">
        <h2>Pagina nu a putut fi afișată</h2>
        <p className="muted">
          A apărut o eroare neașteptată în panou. Simularea de pe server nu este afectată; reîncarcă pagina și
          încearcă din nou.
        </p>
        <button type="button" className="btn btn-primary" onClick={() => window.location.reload()}>
          Reîncarcă pagina
        </button>
      </div>
    )
  }
}
