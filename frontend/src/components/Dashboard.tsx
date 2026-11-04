import { FormEvent, useEffect, useState } from 'react'
import { api } from '../core/api'
import { useAuth } from '../core/auth/AuthContext'
import { Link } from 'react-router-dom'
import AdminPanel from './AdminPanel'

interface Module {
  name: string
  display_name: string | null
  description: string | null
  version: string | null
  is_core: boolean
}

const MODULE_ICONS: Record<string, string> = {
  people: '👤',
  places: '📍',
  events: '📅',
  knowledge: '📚',
}

export default function Dashboard() {
  const { user } = useAuth()
  const [modules, setModules] = useState<Module[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<{ id: string; module: string; title: string; summary: string }[]>([])
  const [searching, setSearching] = useState(false)

  async function search(event: FormEvent) {
    event.preventDefault()
    if (query.trim().length < 2) return setResults([])
    setSearching(true)
    try { setResults(await api.get<{ id: string; module: string; title: string; summary: string }[]>(`/search?q=${encodeURIComponent(query.trim())}`)) }
    catch { setResults([]) }
    finally { setSearching(false) }
  }

  useEffect(() => {
    api
      .get<Module[]>('/core/modules/active')
      .then(setModules)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-10">
      <form onSubmit={search} className="flex gap-2" role="search">
        <input aria-label="Search LifeHub" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search people, places, events, knowledge…" className="min-w-0 flex-1 rounded-xl border border-zinc-800 bg-zinc-900 px-4 py-3 text-sm text-zinc-100 placeholder-zinc-600 focus:border-indigo-500 focus:outline-none" />
        <button className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50" disabled={searching}>{searching ? 'Searching…' : 'Search'}</button>
      </form>
      {results.length > 0 && <section className="space-y-2" aria-live="polite">{results.map((item) => <Link key={`${item.module}:${item.id}`} to={`/modules/${item.module}`} className="block rounded-xl border border-zinc-800 bg-zinc-900 p-4 hover:border-indigo-700"><span className="text-xs uppercase tracking-wide text-indigo-400">{item.module}</span><h2 className="mt-1 text-sm font-medium text-zinc-100">{item.title}</h2><p className="mt-1 text-sm text-zinc-500">{item.summary}</p></Link>)}</section>}
      {/* Welcome */}
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100">
          Welcome back, {user?.display_name ?? user?.username}
        </h1>
        <p className="text-zinc-500 mt-1 text-sm">LifeHub is running.</p>
      </div>

      {/* Active modules */}
      <section>
        <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-widest mb-4">
          Active Modules
        </h2>

        {loading ? (
          <p className="text-sm text-zinc-600 font-mono">loading…</p>
        ) : modules.length === 0 ? (
          <div className="border border-zinc-800 border-dashed rounded-xl p-8 text-center">
            <p className="text-sm text-zinc-500">No modules are enabled.</p>
            <p className="text-xs text-zinc-600 mt-2">
              Edit{' '}
              <code className="bg-zinc-900 text-indigo-400 px-1.5 py-0.5 rounded text-xs font-mono">
                config/instance.yaml
              </code>{' '}
              and restart to enable modules.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {modules.map((mod) => (
              <Link
                key={mod.name}
                to={`/modules/${mod.name}`}
                className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex items-start gap-4"
              >
                <span className="text-2xl leading-none mt-0.5">
                  {MODULE_ICONS[mod.name] ?? '🔷'}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium text-zinc-100 text-sm">
                      {mod.display_name ?? mod.name}
                    </h3>
                    <span className="text-xs bg-indigo-950 text-indigo-400 border border-indigo-800/50 px-1.5 py-0.5 rounded-full">
                      active
                    </span>
                  </div>
                  {mod.description && (
                    <p className="text-xs text-zinc-500 mt-1">{mod.description}</p>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* System info (admin only) */}
      {user?.is_system_admin && (
        <section>
          <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-widest mb-4">
            System
          </h2>
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-5 text-sm">
              <div>
                <dt className="text-zinc-500 text-xs">Username</dt>
                <dd className="text-zinc-100 font-mono mt-1">{user.username}</dd>
              </div>
              <div>
                <dt className="text-zinc-500 text-xs">Role</dt>
                <dd className="text-zinc-100 mt-1">Administrator</dd>
              </div>
              <div>
                <dt className="text-zinc-500 text-xs">API docs</dt>
                <dd className="mt-1">
                  <a
                    href="/api/docs"
                    target="_blank"
                    rel="noreferrer"
                    className="text-indigo-400 hover:text-indigo-300 transition-colors text-xs font-mono"
                  >
                    /api/docs ↗
                  </a>
                </dd>
              </div>
            </dl>
          </div>
        </section>
      )}
      {user?.is_system_admin && <AdminPanel />}
    </div>
  )
}
