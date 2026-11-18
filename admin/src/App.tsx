import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { ApiError } from './api/client'
import { AuthProvider } from './components/AuthProvider'
import { ErrorBoundary } from './components/ErrorBoundary'
import { HouseDrawer } from './components/HouseDrawer'
import { Layout } from './components/Layout'
import { RequireAuth } from './components/RequireAuth'
import { ToastProvider } from './components/ToastProvider'
import { HousesPage } from './pages/HousesPage'
import { LoginPage } from './pages/LoginPage'
import { NeighbourhoodPage } from './pages/NeighbourhoodPage'
import { OverviewPage } from './pages/OverviewPage'
import { SimulationPage } from './pages/SimulationPage'
import { UsersPage } from './pages/UsersPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5_000,
      refetchOnWindowFocus: false,
      retry: (count, error) => !(error instanceof ApiError && error.status < 500 && error.status > 0) && count < 2,
    },
  },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter basename="/admin">
            <ErrorBoundary>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route element={<RequireAuth />}>
                  <Route element={<Layout />}>
                    <Route index element={<OverviewPage />} />
                    <Route path="case" element={<HousesPage />}>
                      <Route path=":houseId" element={<HouseDrawer />} />
                    </Route>
                    <Route path="cartier" element={<NeighbourhoodPage />} />
                    <Route path="simulare" element={<SimulationPage />} />
                    <Route path="utilizatori" element={<UsersPage />} />
                  </Route>
                </Route>
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </ErrorBoundary>
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
  )
}
