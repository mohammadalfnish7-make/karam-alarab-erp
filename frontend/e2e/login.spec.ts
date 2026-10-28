import { expect, test } from '@playwright/test'

import { adminEmail, adminPassword, loginAs } from './helpers'

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
    test.skip(!adminPassword, 'Set E2E_ADMIN_PASSWORD to run against a live API')
    await loginAs(page, adminEmail, adminPassword)
    await expect(page.getByRole('status')).toContainText(adminEmail)
  })
})
