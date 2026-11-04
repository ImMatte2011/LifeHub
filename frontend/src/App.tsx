import { Navigate, Route, Routes } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import Layout from './components/Layout'
import LoginPage from './core/auth/LoginPage'
import ProtectedRoute from './core/auth/ProtectedRoute'
import { AuthProvider } from './core/auth/AuthContext'
import ModulesPage from './modules/ModulesPage'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
            <Layout><Dashboard /></Layout>
            </ProtectedRoute>
          }
        />
        <Route path="/modules/:module" element={<ProtectedRoute><Layout><ModulesPage /></Layout></ProtectedRoute>} />
        {/* Fallback: redirect a root */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
