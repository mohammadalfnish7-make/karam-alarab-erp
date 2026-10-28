import { expect, test, type Page } from '@playwright/test'

import { adminEmail, adminPassword, loginAs } from './helpers'

test.describe('Task manager', () => {
  test.skip(!adminPassword, 'Set E2E_ADMIN_PASSWORD to run')

  test('workflow, task, board drag, priorities, due dates, comment, file, activity', async ({
    page,
  }) => {
    test.setTimeout(90_000)
    await loginAs(page, adminEmail, adminPassword)

    const suffix = Date.now().toString(36)
    const workflowName = `WF ${suffix}`
    const typeKey = `ops_${suffix}`
    const typeName = `Ops ${suffix}`
    const taskTitle = `Cargo check ${suffix}`

    await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Workflows' }).click()
    await expect(page.getByRole('heading', { name: 'Workflows and task types' })).toBeVisible()

    await page.getByRole('button', { name: 'New workflow' }).click()
    await page.getByLabel('Workflow name').fill(workflowName)
    await page.getByRole('button', { name: 'Save' }).click()
    await expect(page.getByText(workflowName)).toBeVisible()

    await page.getByRole('button', { name: 'New task type' }).click()
    await page.getByLabel('Type key').fill(typeKey)
    await page.getByLabel('Type name').fill(typeName)
    await page.getByLabel('Workflow').selectOption({ label: workflowName })
    await page.getByRole('button', { name: 'Save' }).click()
    await expect(page.getByText(typeName)).toBeVisible()

    await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Tasks' }).click()
    // Admins land on All tasks by default.
    await expect(
      page.getByRole('heading', { name: /^(My|All) tasks$/ }),
    ).toBeVisible()
    await page.getByRole('button', { name: 'New task' }).click()
    const create = page.getByRole('dialog', { name: 'Create task' })
    await create.getByLabel(/Title/).fill(taskTitle)
    await create.getByLabel('Task type').selectOption({ label: typeName })
    // Directory load auto-assigns the current user; wait until they appear.
    await expect(create.getByText(adminEmail)).toBeVisible({ timeout: 15_000 })
    await create.getByLabel('Priority').selectOption({ label: 'High' })
    await create.getByLabel('Due date').fill('2026-11-20')
    await create.getByRole('button', { name: 'Create' }).click()
    await expect(create).toBeHidden({ timeout: 15_000 })
    await expect(page.getByRole('link', { name: taskTitle })).toBeVisible()

    await page.getByRole('tab', { name: 'Board' }).click()
    await expect(page.getByRole('heading', { name: 'Board' })).toBeVisible()
    await page.getByLabel('Task type').selectOption({ label: typeName })
    const card = page.locator('li').filter({ hasText: taskTitle }).first()
    await expect(card).toBeVisible()
    const doingColumn = page.locator('section[aria-label="Doing"]')
    await card.dragTo(doingColumn)
    await expect(doingColumn.getByRole('link', { name: taskTitle })).toBeVisible({
      timeout: 10_000,
    })

    await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Priorities' }).click()
    await expect(page.getByRole('heading', { name: 'Priorities' })).toBeVisible()
    const priorityRow = page.locator('li').filter({ hasText: taskTitle })
    await priorityRow.getByLabel('Change priority').selectOption({ label: 'Urgent' })
    await expect(
      page
        .locator('section')
        .filter({ has: page.getByRole('heading', { name: /Urgent/ }) })
        .locator('li')
        .filter({ hasText: taskTitle }),
    ).toBeVisible({ timeout: 10_000 })

    await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Due dates' }).click()
    await expect(page.getByRole('heading', { name: 'Due dates' })).toBeVisible()
    const dueRow = page.locator('li').filter({ hasText: taskTitle })
    await dueRow.getByLabel('Change due date').fill('2026-11-25')
    await expect(dueRow.getByLabel('Change due date')).toHaveValue('2026-11-25')

    await dueRow.getByRole('link').first().click()
    // Detail heading prefers the human reference; title stays as subtitle.
    await expect(page.getByText(taskTitle)).toBeVisible()
    await page.getByPlaceholder('Write a comment…').fill('Ready for unload')
    await page.getByRole('button', { name: 'Add comment' }).click()
    await expect(page.getByText('Ready for unload')).toBeVisible()

    await uploadCatalogFile(page, `note-${suffix}.txt`, 'seal checked')
    await expect(page.getByText('File linked to this task.')).toBeVisible({ timeout: 10_000 })

    await expect(page.getByRole('heading', { name: 'Activity' })).toBeVisible()
    await expect(page.getByText(/Created|Status|Commented|Linked/i).first()).toBeVisible()
  })
})

async function uploadCatalogFile(page: Page, name: string, body: string): Promise<void> {
  const fileInput = page.locator('label').filter({ hasText: 'Upload' }).locator('input[type="file"]')
  await fileInput.setInputFiles({
    name,
    mimeType: 'text/plain',
    buffer: Buffer.from(body, 'utf8'),
  })
}
