import { FormEvent, useEffect, useState } from 'react'
import { api } from '../core/api'
import { User } from '../core/auth/AuthContext'

type AdminUser = Pick<User, 'id' | 'username' | 'is_active' | 'is_system_admin' | 'role_id'> & { email: string | null }
type Permission = { resource: string; action: string }
type Role = { id: number; name: string; description: string | null; permissions: Permission[] }
const input = 'rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:border-indigo-500 focus:outline-none'
const button = 'rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-700'
const resources = ['people', 'places', 'events', 'knowledge', 'buildings', 'shared']
const actions = ['read', 'create', 'update', 'delete']

function PermissionMatrix({ selected = [] }: { selected?: Permission[] }) {
  return <div className="overflow-x-auto"><table className="w-full text-left text-xs text-zinc-400"><thead><tr><th className="py-2 pr-4 font-normal">Module</th>{actions.map((action) => <th key={action} className="px-2 py-2 font-normal">{action}</th>)}</tr></thead><tbody>{resources.map((resource) => <tr key={resource} className="border-t border-zinc-800"><th className="py-2 pr-4 font-normal">{resource}</th>{actions.map((action) => <td key={action} className="px-2 py-2"><input aria-label={`${action} ${resource}`} type="checkbox" name="permission" value={`${resource}:${action}`} defaultChecked={selected.some((permission) => permission.resource === resource && permission.action === action)} /></td>)}</tr>)}</tbody></table></div>
}

function readPermissions(form: FormData): Permission[] {
  return form.getAll('permission').map((value) => {
    const [resource, action] = String(value).split(':')
    return { resource, action }
  })
}

export default function AdminPanel() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [enabled, setEnabled] = useState(false)
  const [message, setMessage] = useState('')

  async function load() {
    try {
      const [settings, userList, roleList] = await Promise.all([
        api.get<{ items: { key: string; value: { enabled?: boolean } }[] }>('/core/settings'),
        api.get<AdminUser[]>('/core/admin/users'),
        api.get<Role[]>('/core/admin/roles'),
      ])
      setEnabled(Boolean(settings.items.find((item) => item.key === 'multi_user_enabled')?.value.enabled))
      setUsers(userList); setRoles(roleList)
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not load admin tools') }
  }
  useEffect(() => { void load() }, [])

  async function toggle() {
    try { await api.put('/core/settings/multi_user_enabled', { enabled: !enabled }); setEnabled(!enabled); setMessage('Instance setting saved') }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Could not save setting') }
  }

  async function addUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    try {
      await api.post('/core/admin/users', { username: form.get('username'), password: form.get('password'), email: form.get('email') || null, display_name: form.get('display_name') || null, role_id: form.get('role_id') ? Number(form.get('role_id')) : null })
      event.currentTarget.reset(); setMessage('User created'); await load()
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not create user') }
  }

  async function toggleUser(user: AdminUser) {
    try { await api.patch(`/core/admin/users/${user.id}`, { is_active: !user.is_active }); await load() }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Could not update user') }
  }

  async function addRole(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const permissions = readPermissions(form)
    try { await api.post('/core/admin/roles', { name: form.get('name'), description: form.get('description') || null, permissions }); event.currentTarget.reset(); setMessage('Role created with selected permissions'); await load() }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Could not create role') }
  }

  async function editRole(role: Role, event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const permissions = readPermissions(form)
    try { await api.patch(`/core/admin/roles/${role.id}`, { permissions }); setMessage(`Permissions updated for ${role.name}`); await load() }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Could not update permissions') }
  }

  async function setUserRole(userId: string, roleId: number | null) {
    try { await api.patch(`/core/admin/users/${userId}`, { role_id: roleId }); setMessage('User role updated'); await load() }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Could not update role') }
  }

  return <section className="space-y-5 rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5 sm:p-7">
    <div className="flex flex-wrap items-center justify-between gap-4"><div><h2 className="text-lg font-medium">Administration</h2><p className="mt-1 text-sm text-zinc-500">Accounts and instance access</p></div><button className={button} onClick={toggle}>Multiple accounts: {enabled ? 'On' : 'Off'}</button></div>
    {enabled && <><div className="space-y-2">{users.map((user) => <div key={user.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-zinc-800 p-3"><div><p className="text-sm text-zinc-100">{user.username}{user.is_system_admin && <span className="ml-2 text-xs text-indigo-400">admin</span>}</p><p className="text-xs text-zinc-500">{user.is_active ? 'active' : 'disabled'}</p></div>{!user.is_system_admin && <div className="flex gap-2"><select aria-label={`Role for ${user.username}`} value={user.role_id ?? ''} onChange={(event) => void setUserRole(user.id, event.target.value ? Number(event.target.value) : null)} className={input}><option value="">No role</option>{roles.map((role) => <option key={role.id} value={role.id}>{role.name}</option>)}</select><button onClick={() => void toggleUser(user)} className={button}>{user.is_active ? 'Disable' : 'Enable'}</button></div>}</div>)}</div>
      <form onSubmit={addUser} className="grid gap-2 sm:grid-cols-2"><input required name="username" placeholder="Username" className={input} /><input required minLength={12} name="password" type="password" placeholder="Initial password (12+ characters)" className={input} /><input name="display_name" placeholder="Display name" className={input} /><input name="email" type="email" placeholder="Email (optional)" className={input} /><select required name="role_id" className={input}><option value="">Choose a role</option>{roles.map((role) => <option key={role.id} value={role.id}>{role.name}</option>)}</select><button className={button}>Create user</button></form>
      <div className="space-y-2">{roles.map((role) => <details key={role.id} className="rounded-lg border border-zinc-800 p-3"><summary className="cursor-pointer text-sm text-zinc-200">{role.name} · {role.permissions.length} permissions</summary><form onSubmit={(event) => void editRole(role, event)} className="mt-3 space-y-3"><PermissionMatrix selected={role.permissions} /><button className={button}>Save permissions</button></form></details>)}</div>
      <form onSubmit={addRole} className="space-y-3 rounded-lg border border-zinc-800 p-3"><PermissionMatrix /><div className="flex flex-wrap gap-2"><input required name="name" placeholder="New role name" className={input} /><input name="description" placeholder="Description" className={`${input} flex-1`} /><button className={button}>Create role</button></div></form></>}
    {message && <p className="text-sm text-zinc-400" role="status">{message}</p>}
  </section>
}
