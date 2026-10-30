import { expect, test } from "@playwright/test";

/**
 * Smoke E2E for Phase 5.
 * Requires a running frontend (`bun run dev`) and optional auth credentials:
 *   E2E_EMAIL / E2E_PASSWORD for authenticated flows.
 * Full upload/chat against live OpenRouter/Pinecone is manual — see README.
 */

test.describe("public landing", () => {
  test("shows product copy and auth CTAs", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "Ask your documents",
    );
    await expect(page.getByText("Supported files")).toBeVisible();
  });
});

test.describe("auth gates", () => {
  test("unauthenticated settings redirects to sign-in", async ({ page }) => {
    await page.goto("/settings");
    await expect(page).toHaveURL(/sign-in|auth/i);
  });

  test("unauthenticated documents redirects to sign-in", async ({ page }) => {
    await page.goto("/documents");
    await expect(page).toHaveURL(/sign-in|auth/i);
  });
});

test.describe("authenticated smoke", () => {
  test.skip(
    !process.env.E2E_EMAIL || !process.env.E2E_PASSWORD,
    "Set E2E_EMAIL and E2E_PASSWORD to run authenticated smoke",
  );

  test("sign-in reaches documents", async ({ page }) => {
    await page.goto("/auth/sign-in");
    await page.getByLabel(/email/i).fill(process.env.E2E_EMAIL!);
    await page.getByLabel(/password/i).fill(process.env.E2E_PASSWORD!);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/documents|chat/i, { timeout: 30_000 });
  });
});
