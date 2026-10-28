import { expect, test } from '@playwright/test'

import { adminEmail, adminPassword, loginAs } from './helpers'

test.describe('account password', () => {
  test.beforeEach(() => {
    test.skip(!adminPassword, 'Set E2E_ADMIN_PASSWORD (and API) to run identity e2e')
  })

  test('validates empty and mismatched passwords', async ({ page }) => {
    await loginAs(page, adminEmail, adminPassword)
    await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Password' }).click()
    await expect(page.getByRole('heading', { name: 'Change password' })).toBeVisible()
    await page.getByRole('button', { name: 'Update password' }).click()
    await expect(page.getByText('Enter your current password.')).toBeVisible()
    await expect(page.getByText('Enter a new password.')).toBeVisible()

    await page.getByLabel('Current password').fill(adminPassword)
    await page.getByLabel('New password', { exact: true }).fill('brand-new-password-99')
    await page.getByLabel('Confirm new password').fill('different-password')
    await page.getByRole('button', { name: 'Update password' }).click()
    await expect(page.getByText('New password and confirmation do not match.')).toBeVisible()
  })

  test('wrong current password shows field error', async ({ page }) => {
    await loginAs(page, adminEmail, adminPassword)
    await page.goto('/en/account/password')
    await page.getByLabel('Current password').fill('wrong-current-password')
    await page.getByLabel('New password', { exact: true }).fill('brand-new-password-99')
    await page.getByLabel('Confirm new password').fill('brand-new-password-99')
    await page.getByRole('button', { name: 'Update password' }).click()
    await expect(page.getByText('Current password is incorrect.')).toBeVisible()
  })
})
