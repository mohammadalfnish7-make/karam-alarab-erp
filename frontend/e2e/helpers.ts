import { expect, type Page } from '@playwright/test'

export const adminEmail = process.env.E2E_ADMIN_EMAIL ?? 'admin@karam-alarab.com'
export const adminPassword = process.env.E2E_ADMIN_PASSWORD ?? ''
export const opsEmail = process.env.E2E_OPS_EMAIL ?? 'ops@karam-alarab.com'
export const opsPassword = process.env.E2E_OPS_PASSWORD ?? ''

export async function signOut(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
}

export async function loginAs(page: Page, email: string, password: string): Promise<void> {
  await page.goto('/en/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: 'Operations workspace' })).toBeVisible()
}

export function uniqueEmail(prefix: string): string {
  return `${prefix}.${Date.now()}@example.com`
}
