import { useAuth } from '../core/auth/AuthContext'
import { Link } from 'react-router-dom'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      {/* Header */}
      <header className="border-b border-zinc-800/60 bg-zinc-950/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link to="/" className="text-base font-semibold tracking-tight text-zinc-100">
            Life<span className="text-indigo-400">Hub</span>
          </Link>

          <div className="flex items-center gap-4">
            <span className="text-sm text-zinc-400 hidden sm:block">
              {user?.display_name ?? user?.username}
            </span>
            <button
              onClick={logout}
              className="text-xs text-zinc-500 hover:text-zinc-200 transition-colors font-medium uppercase tracking-wider"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 py-8">
        {children}
      </main>
    </div>
  )
}
