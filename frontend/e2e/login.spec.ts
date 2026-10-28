import { expect, test } from '@playwright/test'

/**
 * Requires API on :8000 with seeded admin.
 * Set E2E_ADMIN_EMAIL / E2E_ADMIN_PASSWORD or defaults match backend .env.example email.
 */
const email = process.env.E2E_ADMIN_EMAIL ?? 'admin@karam-alarab.com'
const password = process.env.E2E_ADMIN_PASSWORD ?? ''

test.describe('login', () => {
  test('shows English login form', async ({ page }) => {
    await page.goto('/en/login')
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
    await expect(page.getByLabel('Email')).toBeVisible()
    await expect(page.getByLabel('Password')).toBeVisible()
  })

  test('shows Russian login form', async ({ page }) => {
    await page.goto('/ru/login')
    await expect(page.getByRole('heading', { name: 'Вход' })).toBeVisible()
  })

  test('rejects empty submit with field errors', async ({ page }) => {
    await page.goto('/en/login')
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByText('Enter your email.')).toBeVisible()
    await expect(page.getByText('Enter your password.')).toBeVisible()
  })

  test('signs in with seed admin when password is configured', async ({ page }) => {
    test.skip(!password, 'Set E2E_ADMIN_PASSWORD to run against a live API')
    await page.goto('/en/login')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByRole('heading', { name: 'Operations workspace' })).toBeVisible()
    await expect(page.getByText(new RegExp(email, 'i'))).toBeVisible()
  })
})
