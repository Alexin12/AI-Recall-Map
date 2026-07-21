import { test, expect } from "@playwright/test";

/**
 * Core happy path (mirrors backend/tests/test_e2e_core_loop.py): paste a
 * Material on the Global Home, confirm the proposed Topic with a Goal,
 * review the resulting Concept, then check the Concept Map.
 *
 * LLM output is canned via LLM_FAKE=1 (see backend/app/llm.py): extraction
 * always returns one Concept "Ser vs estar", which always lands as an
 * orphan proposed into a Topic named "Spanish".
 */
test("paste -> extract -> confirm -> review -> map", async ({ page }) => {
  await page.goto("/");

  await page.getByTestId("paste-textarea").fill("Ser is for essence; estar is for states.");
  await page.getByTestId("paste-submit").click();

  await expect(page.getByTestId("paste-status")).toContainText(
    "Routed — see where each concept landed below",
  );

  await expect(page.getByTestId("proposal-name-input")).toHaveValue("Spanish");
  await page.getByTestId("proposal-goal-input").fill("Learn Spanish for travel");
  await page.getByTestId("proposal-create-button").click();

  await expect(page.getByTestId("paste-status")).toContainText('Created "Spanish"');

  await page.getByRole("link", { name: "Go to topics" }).click();
  await page.getByRole("link", { name: "Spanish" }).click();

  await expect(page.getByTestId("concept-map")).toContainText("Ser vs estar");
  await expect(page.locator("table")).toContainText("core");
  await expect(page.getByText("1 concept(s) due now:")).toBeVisible();

  await page.getByRole("link", { name: "Start review" }).click();

  await page.getByTestId("review-answer-textarea").fill("Ser expresses essence.");
  await page.getByTestId("review-submit-button").click();

  await expect(page.getByTestId("review-verdict")).toContainText("Verdict: pass");

  await page.getByRole("link", { name: "Back to topic" }).click();
  await expect(page.getByText("Nothing due right now — all caught up.")).toBeVisible();
});
