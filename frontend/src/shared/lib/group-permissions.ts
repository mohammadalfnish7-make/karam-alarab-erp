/** Group `resource:action` names by resource for the permissions checklist. */
export function groupPermissions(names: readonly string[]): Record<string, string[]> {
  const groups: Record<string, string[]> = {}
  for (const name of names) {
    const sep = name.indexOf(':')
    const resource = sep === -1 ? name : name.slice(0, sep)
    const list = groups[resource] ?? []
    list.push(name)
    groups[resource] = list
  }
  for (const key of Object.keys(groups)) {
    groups[key]?.sort()
  }
  return Object.fromEntries(Object.entries(groups).sort(([a], [b]) => a.localeCompare(b)))
}
