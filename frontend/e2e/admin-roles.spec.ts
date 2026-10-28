import { expect, test } from '@playwright/test'

import { adminEmail, adminPassword, loginAs, signOut, uniqueEmail } from './helpers'

test.describe('admin roles', () => {
  test.beforeEach(() => {
    test.skip(!adminPassword, 'Set E2E_ADMIN_PASSWORD (and API) to run identity e2e')
  })

  test('admin opens roles and edits operations permissions with confirm', async ({ page }) => {
    await loginAs(page, adminEmail, adminPassword)
    await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Roles' }).click()
    await expect(page.getByRole('heading', { name: 'Roles' })).toBeVisible()

    const operations = page.getByRole('row', { name: /Operations/ })
    await operations.getByRole('button', { name: 'Edit permissions' }).click()
    await expect(page.getByRole('dialog', { name: /Permissions/ })).toBeVisible()
    await page.getByRole('dialog', { name: /Permissions/ }).getByRole('button', { name: 'Save' }).click()
    const confirm = page.getByRole('alertdialog')
    await expect(confirm).toBeVisible()
    await expect(confirm.getByText('Replace role permissions?')).toBeVisible()
    await confirm.getByRole('button', { name: 'Cancel' }).click()
    await expect(confirm).toHaveCount(0)
  })

  test('register permission validates format', async ({ page }) => {
    await loginAs(page, adminEmail, adminPassword)
    await page.goto('/en/admin/roles')
    await page.getByRole('button', { name: 'Register permission' }).click()
    await page.getByRole('button', { name: 'Add permission' }).click()
    await expect(page.getByText('Enter a permission name.')).toBeVisible()
    await page.getByLabel('Permission name').fill('Not Valid')
    await page.getByRole('button', { name: 'Add permission' }).click()
    await expect(
      page.getByText('Use the form resource:action (letters, numbers, underscore).'),
    ).toBeVisible()
  })

  test('ops cannot open roles admin', async ({ page }) => {
    const email = uniqueEmail('ops-roles')
    const password = 'e2e-password-12'
    await loginAs(page, adminEmail, adminPassword)
    const created = await page.request.post('/api/users', {
      data: { email, password, roles: ['operations'] },
    })
    expect(created.ok()).toBeTruthy()
    await signOut(page)
    await loginAs(page, email, password)
    await page.goto('/en/admin/roles')
    await expect(page.getByText('You do not have access')).toBeVisible()
  })
})
