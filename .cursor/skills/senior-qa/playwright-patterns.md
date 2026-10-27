# Playwright patterns

## Locator order

```ts
page.getByRole('button', { name: 'Create shipment' });
page.getByLabel('Weight (kg)');
page.getByText('In transit');
page.getByTestId('shipment-status'); // last resort, stable contract
```

Do not use `page.locator('button.btn-primary.mt-2')`.

## Isolation

```ts
test.beforeEach(async ({ page }) => {
  const user = await seedSalesUser();
  await login(page, user);
});

test('sales creates a cosmetics quote', async ({ page }) => {
  await page.goto('/en/quotes/new');
  await page.getByLabel('Type of goods').fill('Cosmetics');
  await page.getByRole('button', { name: 'Create quote' }).click();
  await expect(page.getByRole('status')).toHaveText(/quote created/i);
});
```

Seed unique customers per test (timestamp or uuid in the name).

## Authz check

```ts
test('ops cannot open another customer shipment', async ({ page, request }) => {
  const { otherShipmentId } = await seedForeignShipment();
  await page.goto(`/en/shipments/${otherShipmentId}`);
  await expect(page.getByRole('heading', { name: /not found|forbidden/i })).toBeVisible();
});
```

Expect 404 or a forbidden screen. Never assert on leaked cargo details.

## Soft checks

Use `expect.soft` only on a checklist of visible labels after a page load. Do not soft-assert money posts.

## CI

- `npx playwright install chromium --with-deps`
- Trace: `on-first-retry`
- Shard if the suite exceeds a few minutes
