import { FormEvent, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../core/api'
import MapView from './MapView'

type Row = Record<string, unknown>
type Definition = { name: string; label: string; data_type: string; required: boolean; enum_values?: string[] | null }
type KnowledgeType = { name: string; label: string; properties: Definition[] }

const inputClass = 'w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:border-indigo-500 focus:outline-none'
const buttonClass = 'rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50'

export default function ModulesPage() {
  const { module = '' } = useParams()
  const [rows, setRows] = useState<Row[]>([])
  const [types, setTypes] = useState<KnowledgeType[]>([])
  const [selectedType, setSelectedType] = useState('book')
  const [extensions, setExtensions] = useState<Row[]>([])
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')

  async function refresh() {
    setLoading(true)
    try {
      if (module === 'knowledge') {
        const available = await api.get<KnowledgeType[]>('/knowledge/types')
        setTypes(available)
        if (available.length && !available.some((item) => item.name === selectedType)) setSelectedType(available[0].name)
        setRows(await api.get<Row[]>(`/knowledge${query ? `?q=${encodeURIComponent(query)}` : ''}`))
      } else {
        const endpoint = module === 'people' ? '/people' : module === 'places' ? '/places' : module === 'buildings' ? '/buildings' : '/events'
        setRows(await api.get<Row[]>(`${endpoint}${query ? `?q=${encodeURIComponent(query)}` : ''}`))
        if (module === 'places') setExtensions(await api.get<Row[]>('/core/extensions'))
      }
      setMessage('')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not load data') }
    finally { setLoading(false) }
  }

  useEffect(() => { void refresh() }, [module])

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    try {
      if (module === 'people') await api.post('/people', { display_name: data.get('display_name'), first_name: data.get('first_name') || null, last_name: data.get('last_name') || null, notes: data.get('notes') || null })
      if (module === 'places') await api.post('/places', { name: data.get('name'), description: data.get('description') || null, address: data.get('address') || null, latitude: data.get('latitude') ? Number(data.get('latitude')) : null, longitude: data.get('longitude') ? Number(data.get('longitude')) : null })
      if (module === 'events') await api.post('/events', { title: data.get('title'), description: data.get('description') || null, starts_at: new Date(String(data.get('starts_at'))).toISOString(), ends_at: data.get('ends_at') ? new Date(String(data.get('ends_at'))).toISOString() : null })
      if (module === 'buildings') await api.post('/buildings', { name: data.get('name'), address: data.get('address') || null })
      if (module === 'knowledge') {
        const type = types.find((item) => item.name === selectedType)
        const properties = Object.fromEntries((type?.properties ?? []).map((property) => {
          const raw = data.get(`property:${property.name}`)
          if (!raw) return [property.name, null]
          const value = String(raw)
          return [property.name, property.data_type === 'integer' ? Number.parseInt(value, 10) : property.data_type === 'number' ? Number(value) : property.data_type === 'boolean' ? value === 'true' : value]
        }).filter(([, value]) => value !== null))
        await api.post('/knowledge', { entity_type: selectedType, title: data.get('title'), description: data.get('description') || null, notes: data.get('notes') || null, properties })
      }
      event.currentTarget.reset()
      setMessage('Saved')
      await refresh()
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not save') }
  }

  const title = module.charAt(0).toUpperCase() + module.slice(1)
  const mapEnabled = extensions.some((extension) => extension.name === 'maps' && extension.available)

  return <div className="space-y-8">
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div><p className="text-xs uppercase tracking-widest text-indigo-400">LifeHub module</p><h1 className="mt-2 text-3xl font-semibold text-zinc-100">{title}</h1></div>
      <form onSubmit={(event) => { event.preventDefault(); void refresh() }} className="flex gap-2"><input className={inputClass} value={query} onChange={(e) => setQuery(e.target.value)} placeholder={`Search ${module}`} /><button className={buttonClass}>Search</button></form>
    </div>

    {module === 'places' && <MapView places={rows} enabled={mapEnabled} />}

    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5 sm:p-7">
      <h2 className="mb-5 text-lg font-medium">Add {module === 'knowledge' ? 'an item' : module === 'events' ? 'an event' : module === 'places' ? 'a place' : 'a person'}</h2>
      <form onSubmit={create} className="grid gap-4 sm:grid-cols-2">
        {module === 'people' && <><label className="space-y-1 text-xs text-zinc-400">Display name<input required name="display_name" className={inputClass} /></label><label className="space-y-1 text-xs text-zinc-400">First name<input name="first_name" className={inputClass} /></label><label className="space-y-1 text-xs text-zinc-400">Last name<input name="last_name" className={inputClass} /></label><label className="space-y-1 text-xs text-zinc-400 sm:col-span-2">Notes<textarea name="notes" className={inputClass} rows={2} /></label></>}
        {(module === 'places' || module === 'buildings') && <><label className="space-y-1 text-xs text-zinc-400">Name<input required name="name" className={inputClass} /></label><label className="space-y-1 text-xs text-zinc-400">Address<input name="address" className={inputClass} /></label>{module === 'places' && <><label className="space-y-1 text-xs text-zinc-400">Latitude<input name="latitude" type="number" step="any" className={inputClass} /></label><label className="space-y-1 text-xs text-zinc-400">Longitude<input name="longitude" type="number" step="any" className={inputClass} /></label><label className="space-y-1 text-xs text-zinc-400 sm:col-span-2">Description<textarea name="description" className={inputClass} rows={2} /></label></>}</>}
        {module === 'events' && <><label className="space-y-1 text-xs text-zinc-400">Title<input required name="title" className={inputClass} /></label><label className="space-y-1 text-xs text-zinc-400">Starts<input required name="starts_at" type="datetime-local" className={inputClass} /></label><label className="space-y-1 text-xs text-zinc-400">Ends<input name="ends_at" type="datetime-local" className={inputClass} /></label><label className="space-y-1 text-xs text-zinc-400 sm:col-span-2">Description<textarea name="description" className={inputClass} rows={2} /></label></>}
        {module === 'knowledge' && <><label className="space-y-1 text-xs text-zinc-400">Type<select className={inputClass} value={selectedType} onChange={(e) => setSelectedType(e.target.value)}>{types.map((type) => <option key={type.name} value={type.name}>{type.label}</option>)}</select></label><label className="space-y-1 text-xs text-zinc-400">Title<input required name="title" className={inputClass} /></label>{types.find((type) => type.name === selectedType)?.properties.map((property) => <label key={property.name} className="space-y-1 text-xs text-zinc-400">{property.label}{property.data_type === 'enum' ? <select required={property.required} name={`property:${property.name}`} className={inputClass}><option value="">Select…</option>{property.enum_values?.map((value) => <option key={value}>{value}</option>)}</select> : property.data_type === 'boolean' ? <select required={property.required} name={`property:${property.name}`} className={inputClass}><option value="">Select…</option><option value="true">Yes</option><option value="false">No</option></select> : <input required={property.required} name={`property:${property.name}`} type={property.data_type === 'integer' || property.data_type === 'number' ? 'number' : property.data_type === 'date' ? 'date' : 'text'} className={inputClass} />}</label>)}<label className="space-y-1 text-xs text-zinc-400 sm:col-span-2">Description<textarea name="description" className={inputClass} rows={2} /></label><label className="space-y-1 text-xs text-zinc-400 sm:col-span-2">Notes<textarea name="notes" className={inputClass} rows={2} /></label></>}
        <div className="flex items-center gap-3 sm:col-span-2"><button disabled={loading} className={buttonClass}>Save</button>{message && <span className="text-sm text-zinc-400" role="status">{message}</span>}</div>
      </form>
    </section>

    <section><div className="mb-4 flex items-center justify-between"><h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500">Records</h2><span className="text-xs text-zinc-600">{rows.length}</span></div>{loading ? <p className="text-sm text-zinc-500">Loading…</p> : rows.length === 0 ? <div className="rounded-xl border border-dashed border-zinc-800 p-8 text-center text-sm text-zinc-500">Nothing here yet.</div> : <div className="grid gap-3 md:grid-cols-2">{rows.map((row) => <article key={String(row.id)} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4"><h3 className="font-medium text-zinc-100">{String(row.title ?? row.display_name ?? row.name ?? 'Record')}</h3>{Boolean(row.description) && <p className="mt-1 text-sm text-zinc-400">{String(row.description)}</p>}{Boolean(row.notes) && <p className="mt-1 text-sm text-zinc-400">{String(row.notes)}</p>}<p className="mt-3 text-xs text-zinc-600">{row.starts_at ? new Date(String(row.starts_at)).toLocaleString() : row.address ? String(row.address) : row.entity_type_id ? types.find((type) => type.name === String(row.entity_type))?.label ?? 'Knowledge item' : ''}</p></article>)}</div>}</section>
  </div>
}
