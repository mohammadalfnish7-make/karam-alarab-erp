import { expect, test } from '@playwright/test'

import {
  adminEmail,
  adminPassword,
  loginAs,
  signOut,
  uniqueEmail,
} from './helpers'

test.describe('admin users', () => {
  test.beforeEach(() => {
    test.skip(!adminPassword, 'Set E2E_ADMIN_PASSWORD (and API) to run identity e2e')
  })

  test('admin opens users list and creates an operations user', async ({ page }) => {
    await loginAs(page, adminEmail, adminPassword)
    await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Users' }).click()
    await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible()

    const email = uniqueEmail('e2e-ops')
    await page.getByRole('button', { name: 'Create user' }).click()
    await expect(page.getByRole('dialog', { name: 'Create user' })).toBeVisible()
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Temporary password').fill('e2e-password-12')
    await page.getByRole('checkbox', { name: /Operations/i }).check()
    await page.getByRole('dialog', { name: 'Create user' }).getByRole('button', { name: 'Create user' }).click()
    await expect(page.getByRole('dialog', { name: 'Create user' })).toHaveCount(0)
    await expect(page.getByText(email)).toBeVisible()
  })

  test('create user validates empty fields', async ({ page }) => {
    await loginAs(page, adminEmail, adminPassword)
    await page.goto('/en/admin/users')
    await page.getByRole('button', { name: 'Create user' }).click()
    await page.getByRole('dialog', { name: 'Create user' }).getByRole('button', { name: 'Create user' }).click()
    await expect(page.getByText('Enter an email.')).toBeVisible()
    await expect(page.getByText('Enter a temporary password.')).toBeVisible()
  })

  test('create user rejects short password', async ({ page }) => {
    await loginAs(page, adminEmail, adminPassword)
    await page.goto('/en/admin/users')
    await page.getByRole('button', { name: 'Create user' }).click()
    await page.getByLabel('Email').fill(uniqueEmail('short-pw'))
    await page.getByLabel('Temporary password').fill('short')
    await page.getByRole('dialog', { name: 'Create user' }).getByRole('button', { name: 'Create user' }).click()
    await expect(page.getByText('Password must be at least 12 characters.')).toBeVisible()
  })

  test('duplicate email shows field error', async ({ page }) => {
    await loginAs(page, adminEmail, adminPassword)
    await page.goto('/en/admin/users')
    const email = uniqueEmail('dup')
    await page.getByRole('button', { name: 'Create user' }).click()
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Temporary password').fill('e2e-password-12')
    await page.getByRole('dialog', { name: 'Create user' }).getByRole('button', { name: 'Create user' }).click()
    await expect(page.getByText(email)).toBeVisible()

    await page.getByRole('button', { name: 'Create user' }).click()
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Temporary password').fill('e2e-password-12')
    await page.getByRole('dialog', { name: 'Create user' }).getByRole('button', { name: 'Create user' }).click()
    await expect(page.getByText('A user with this email already exists.')).toBeVisible()
  })

  test('search filters the visible users', async ({ page }) => {
    await loginAs(page, adminEmail, adminPassword)
    await page.goto('/en/admin/users')
    const table = page.getByRole('table')
    await page.getByLabel('Search').fill(adminEmail)
    await expect(table.getByText(adminEmail)).toBeVisible()
    await page.getByLabel('Search').fill('no-such-user-xyz')
    await expect(table.getByText(adminEmail)).toHaveCount(0)
  })

  test('ops user is forbidden from admin users', async ({ page }) => {
    const email = uniqueEmail('ops-forbid')
    const password = 'e2e-password-12'
    await loginAs(page, adminEmail, adminPassword)
    const created = await page.request.post('/api/users', {
      data: { email, password, roles: ['operations'] },
    })
    expect(created.ok()).toBeTruthy()
    await signOut(page)
    await loginAs(page, email, password)
    await expect(page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Users' })).toHaveCount(0)
    await page.goto('/en/admin/users')
    await expect(page.getByText('You do not have access')).toBeVisible()
    await page.getByRole('button', { name: 'Go to home' }).click()
    await expect(page.getByRole('heading', { name: 'Operations workspace' })).toBeVisible()
  })

  test('russian users page has translated title', async ({ page }) => {
    await loginAs(page, adminEmail, adminPassword)
    await page.goto('/ru/admin/users')
    await expect(page.getByRole('heading', { name: 'Пользователи' })).toBeVisible()
  })
})
