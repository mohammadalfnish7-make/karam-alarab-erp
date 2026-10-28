/** TanStack Query keys for auth. Keep here so invalidation stays one place. */
export const sessionKeys = {
  all: ['session'] as const,
  me: () => [...sessionKeys.all, 'me'] as const,
}
