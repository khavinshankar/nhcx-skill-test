import { Locator, Page, TestInfo, expect, test } from "@playwright/test";
import { execFileSync } from "child_process";
import fs from "fs";
import path from "path";

// Shared parts of the NHCX GUI runner (T2G): the backend bridge (payer driver,
// test data, report merge), the report entry and the screen steps every test uses.

const E2E_DIR = path.resolve(
  __dirname,
  process.env.NHCX_TEST_E2E_DIR || "../../../care/care/nhcx/tests/e2e",
);
const ARTIFACTS = path.join(E2E_DIR, "artifacts/gui");
const CONTAINER =
  process.env.NHCX_TEST_BACKEND_CONTAINER || "care-nhcx-backend";
const CONTAINER_E2E_DIR =
  process.env.NHCX_TEST_CONTAINER_E2E_DIR || "/app/care/nhcx/tests/e2e";

export const WAIT_MS = Number(process.env.NHCX_TEST_WAIT_SECONDS || 120) * 1000;
const POLL_AFTER_MS =
  Number(process.env.NHCX_TEST_POLL_AFTER_SECONDS || 30) * 1000;

export type Cause = "ours" | "sandbox" | "setup" | "";

export class Stop extends Error {
  constructor(
    message: string,
    public result: "blocked" | "skipped" | "fail",
    public cause: Cause,
  ) {
    super(message);
  }
}

/** Runs `manage.py nhcx_e2e <args>` in the backend; returns its JSON line. */
export function backend<T = Record<string, unknown>>(...args: string[]): T {
  const out = execFileSync(
    "docker",
    ["exec", CONTAINER, "python", "manage.py", "nhcx_e2e", ...args],
    { encoding: "utf-8", stdio: ["ignore", "pipe", "pipe"], timeout: 600000 },
  );
  const line = out
    .split("\n")
    .reverse()
    .find((l) => l.trim().startsWith("{"));
  if (!line) throw new Error(`nhcx_e2e ${args[0]} returned no JSON`);
  return JSON.parse(line) as T;
}

export interface Info {
  facility: string;
  user: string;
  doctor: string;
  diagnosis: string;
  pmjay_package: string;
  unknown_member: string;
  payers: Record<
    "irdai" | "pmjay",
    { code: string; member: string; patient: string }
  >;
}

let info: Info | undefined;
export function testData(): Info {
  info ??= backend<Info>("gui-info");
  return info;
}

interface Step {
  at: string;
  what: string;
  result: string;
  got: string;
}

/** One GUI report entry (T2X), built while the test walks the screens. */
export class Entry {
  steps: Step[] = [];
  claims: string[] = [];
  decisions: unknown[] = [];
  private n = 0;
  readonly dir: string;

  constructor(
    readonly id: string,
    readonly page: Page,
  ) {
    this.dir = path.join(ARTIFACTS, id);
    fs.rmSync(this.dir, { recursive: true, force: true });
    fs.mkdirSync(this.dir, { recursive: true });
  }

  async shot(what: string) {
    this.n += 1;
    const name = `${String(this.n).padStart(2, "0")}-${what
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .slice(0, 60)}.png`;
    await this.page
      .screenshot({ path: path.join(this.dir, name), fullPage: true })
      .catch(() => undefined);
  }

  async step(what: string, got: string, result = "pass") {
    this.steps.push({ at: new Date().toISOString(), what, result, got });
    await this.shot(what);
  }

  async check(ok: boolean, what: string, got: string, cause: Cause = "ours") {
    await this.step(what, got, ok ? "pass" : "fail");
    if (!ok) throw new Stop(`${what}: ${got}`, "fail", cause);
  }

  write(result: string, cause: Cause, detail: string) {
    let trail = { correlation_ids: [] as string[], ledger_ids: [] as string[] };
    if (this.claims.length) {
      try {
        trail = backend("gui-trail", ...this.claims);
      } catch {
        // the entry is written without ids rather than lost
      }
    }
    const file = path.join(ARTIFACTS, `${this.id}.json`);
    let attempts = 1;
    try {
      const prev = JSON.parse(fs.readFileSync(file, "utf-8"));
      if (prev.result !== "pass") attempts = (prev.attempts || 0) + 1;
    } catch {
      // first attempt
    }
    const entry = {
      id: this.id,
      runner: "gui",
      claim: this.claims.join(", "),
      correlation_ids: trail.correlation_ids,
      ledger_ids: trail.ledger_ids,
      decisions: this.decisions,
      steps: this.steps,
      result,
      cause,
      detail,
      attempts,
    };
    fs.writeFileSync(file, JSON.stringify(entry, null, 2));
    backend(
      "report-merge",
      `${CONTAINER_E2E_DIR}/artifacts/gui/${this.id}.json`,
    );
  }
}

function chosen(id: string, payer: string) {
  const only = (process.env.NHCX_TEST_ONLY || "")
    .split(/[\s,]+/)
    .filter(Boolean)
    .map((s) => s.toLowerCase());
  return (
    !only.length || only.includes(id.toLowerCase()) || only.includes(payer)
  );
}

/** Declares one T test; its outcome lands in the shared e2e report. */
export function nhcx(
  id: string,
  payer: "irdai" | "pmjay",
  title: string,
  body: (page: Page, e: Entry, info: TestInfo) => Promise<void>,
) {
  if (!chosen(id, payer)) {
    test.skip(`${id} ${title}`, () => {});
    return;
  }
  test(`${id} ${title}`, async ({ page }, testInfo) => {
    const e = new Entry(id, page);
    let result = "pass";
    let cause: Cause = "";
    let detail = "";
    try {
      await body(page, e, testInfo);
    } catch (err) {
      await e.shot("failure");
      if (err instanceof Stop) {
        result = err.result;
        cause = err.cause;
        detail = err.message;
      } else {
        result = "fail";
        cause = "ours";
        detail = String((err as Error).message || err).split("\n")[0];
        e.steps.push({
          at: new Date().toISOString(),
          what: "screen step",
          result: "fail",
          got: detail,
        });
      }
    }
    e.write(result, cause, detail);
    if (result === "fail") throw new Error(detail);
    if (result !== "pass") test.skip(true, `${result}: ${detail}`);
  });
}

/** A test whose GUI walk is not written: recorded as skipped, with the reason. */
export function notDriven(
  id: string,
  payer: "irdai" | "pmjay",
  title: string,
  reason: string,
) {
  nhcx(id, payer, title, async () => {
    throw new Stop(reason, "skipped", "");
  });
}

// ---- screen steps ----

export async function login(page: Page, e: Entry) {
  await page.goto("/login");
  await page
    .getByRole("textbox", { name: /username/i })
    .fill(process.env.NHCX_TEST_USER || "");
  await page.getByLabel(/password/i).fill(process.env.NHCX_TEST_PASSWORD || "");
  await page.getByRole("button", { name: /login/i }).click();
  await expect(page).not.toHaveURL(/\/login/, { timeout: 30000 });
  await e.step("operator signs in", process.env.NHCX_TEST_USER || "");
}

const panel = (page: Page) => page.getByRole("tabpanel");

/** The "<Stage>: <sub>" chip in the claim header. */
export function stageChip(page: Page, stage: string): Locator {
  return page.getByText(new RegExp(`^${stage}: `)).first();
}

/** Waits for the header chip to read one of `wanted`, refreshing as an operator would. */
export async function waitChip(
  page: Page,
  e: Entry,
  stage: string,
  wanted: string[],
  what: string,
  cause: Cause = "sandbox",
): Promise<string> {
  const start = Date.now();
  let last = "";
  while (Date.now() - start < WAIT_MS) {
    const chip = stageChip(page, stage);
    last = ((await chip.textContent().catch(() => "")) || "").trim();
    if (wanted.some((w) => last === `${stage}: ${w}`)) {
      await e.step(
        what,
        `${last} after ${Math.round((Date.now() - start) / 1000)}s`,
      );
      return last;
    }
    const refresh = page.getByRole("button", { name: /^refresh$/i });
    if (Date.now() - start > POLL_AFTER_MS && (await refresh.isVisible())) {
      await refresh.click();
    }
    await page.waitForTimeout(5000);
  }
  const shown = await headerError(page);
  await e.check(
    false,
    what,
    `chip still "${last || "none"}" after ${WAIT_MS / 1000}s` +
      (shown ? `; ${shown}` : ""),
    cause,
  );
  return last;
}

/** The red line under the tabs (a refusal), if any. */
export async function headerError(page: Page): Promise<string> {
  const red = panel(page).locator(
    ".text-red-500, .text-red-600, .text-red-700",
  );
  const n = await red.count();
  for (let i = 0; i < n; i++) {
    const text = ((await red.nth(i).textContent()) || "").trim();
    if (text && text !== "*") return text;
  }
  return "";
}

export async function openTab(page: Page, name: string) {
  await page.getByRole("tab", { name, exact: true }).click();
  await expect(page.getByRole("tab", { name, exact: true })).toHaveAttribute(
    "data-state",
    "active",
  );
}

/** S1 from the patient's chart entry: prefilled, so the case links to the patient. */
export async function openClaim(
  page: Page,
  e: Entry,
  payer: "irdai" | "pmjay",
): Promise<string> {
  const data = testData();
  const p = data.payers[payer];
  const query = new URLSearchParams({
    id_type: "MemberId",
    id_value: p.member,
    ...(p.patient ? { patient: p.patient } : {}),
  });
  await page.goto(`/facility/${data.facility}/claims/search?${query}`);
  await expect(page.locator("#nhcx-id-value")).toHaveValue(p.member);
  await page.getByRole("button", { name: "Search policies" }).click();
  const row = page.getByRole("row").filter({ hasText: p.code }).first();
  try {
    await expect(row).toBeVisible({ timeout: 60000 });
  } catch {
    await e.check(
      false,
      `policy search finds the ${payer.toUpperCase()} member`,
      "no row for the payer",
      "sandbox",
    );
  }
  await e.step(
    `policy search finds the ${payer.toUpperCase()} member`,
    ((await row.textContent()) || "").replace(/\s+/g, " ").slice(0, 160),
  );
  await row.getByRole("button", { name: "Select" }).click();
  await expect(page).toHaveURL(/\/claims\/[0-9a-f-]{36}/, { timeout: 30000 });
  const claimId = page.url().match(/claims\/([0-9a-f-]{36})/)![1];
  e.claims.push(claimId);
  await expect(page.getByRole("tab", { name: "Eligibility" })).toBeVisible();
  await e.step("provider opens the claim", `claim ${claimId}`);
  return claimId;
}

const PURPOSE = {
  validation: "Validation, is the policy in force?",
  discovery: "Discovery, find active coverage",
} as const;

export async function eligibility(
  page: Page,
  e: Entry,
  purpose: keyof typeof PURPOSE,
) {
  await openTab(page, "Eligibility");
  const p = panel(page);
  const trigger = p.getByRole("combobox").first();
  await trigger.click();
  await page.getByRole("option", { name: PURPOSE[purpose] }).click();
  const send = p.getByRole("button", { name: /^(Send to payer|Check again)$/ });
  await send.click();
  const confirm = page.getByRole("button", { name: "Confirm" });
  if (await confirm.isVisible().catch(() => false)) await confirm.click();
  await e.step(`provider sends the ${purpose} check`, PURPOSE[purpose]);
  await page.waitForTimeout(2000);
  await waitChip(
    page,
    e,
    "Eligibility",
    ["In force"],
    `payer answers the ${purpose} check`,
  );
  await expect(p.getByText("Payer verdict")).toBeVisible();
  const sum = p.getByText("Sum insured").first();
  await e.step(
    `${purpose} verdict on screen`,
    (await sum.isVisible()) ? "sum insured shown" : "verdict shown",
  );
}

export async function fetchPlan(page: Page, e: Entry) {
  await openTab(page, "Insurance plan");
  const p = panel(page);
  const fetch = p.getByRole("button", { name: "Fetch insurance plan" });
  if (await fetch.isVisible().catch(() => false)) {
    await fetch.click();
    await e.step("provider requests the plan", "Fetch insurance plan");
  }
  await expect(p.getByText("Plan identifier")).toBeVisible({
    timeout: WAIT_MS,
  });
  await e.step(
    "plan is on the screen",
    ((await p.locator("dl, .grid").first().textContent()) || "")
      .replace(/\s+/g, " ")
      .slice(0, 200),
  );
}

export async function addLine(page: Page, e: Entry, code: string) {
  await openTab(page, "Line items");
  const p = panel(page);
  await p.getByRole("button", { name: "Choose line items" }).click();
  await p.locator("#nhcx-lines-search").fill(code);
  await p.getByRole("button", { name: "Search", exact: true }).click();
  const row = p.getByRole("row").filter({ hasText: code }).first();
  await row.getByRole("button", { name: "Add" }).click();
  await expect(
    p
      .getByRole("row")
      .filter({ hasText: code })
      .filter({ has: page.getByRole("button", { name: "Remove" }) }),
  ).toBeVisible();
  await e.step(`provider quotes ${code} x1`, "line on the pre-authorisation");
  await p.getByRole("button", { name: "Back to the claim" }).click();
}

export async function validate(page: Page, e: Entry) {
  await openTab(page, "Validate");
  const p = panel(page);
  await p
    .getByRole("button", { name: /^(Validate procedure set|Check again)$/ })
    .click();
  const confirm = page.getByRole("button", { name: "Confirm" });
  if (await confirm.isVisible().catch(() => false)) await confirm.click();
  await e.step(
    "provider asks for the auth requirements",
    "Validate procedure set",
  );
  const done = p.getByRole("button", { name: "Check again" });
  await expect(done).toBeVisible({ timeout: WAIT_MS });
  const red = await headerError(page);
  await e.check(
    !red,
    "payer rules on the auth requirements",
    red || "ruling on screen",
    "sandbox",
  );
}

const iso = (d: Date) => d.toISOString().slice(0, 10);

/** S4 + documents + forms on the Pre-authorisation tab. */
export async function fillDraft(page: Page, e: Entry) {
  const data = testData();
  await openTab(page, "Pre-authorisation");
  const p = panel(page);
  const link = p.getByRole("button", { name: "Link", exact: true }).first();
  if (await link.isVisible().catch(() => false)) {
    await link.click();
    await expect(p.getByText("Linked admission")).toBeVisible();
    await e.step("provider links the admission", "Link");
  }
  const today = new Date();
  await p
    .locator("#nhcx-admission-date")
    .fill(iso(new Date(today.getTime() - 86400000)));
  await p
    .locator("#nhcx-discharge-date")
    .fill(iso(new Date(today.getTime() + 3 * 86400000)));
  const icd = p.locator("div:has(> label:text-is('ICD-10 code')) input");
  if (!(await icd.count()))
    await p.getByRole("button", { name: "Add diagnosis" }).click();
  await icd.first().fill(data.diagnosis);
  const addDoctor = p.getByRole("button", { name: "Add doctor" });
  if (await addDoctor.isVisible().catch(() => false)) {
    const doctor = p.locator(
      "div:has(> label:text-is('Doctor')) button[role=combobox]",
    );
    if (!(await doctor.count())) await addDoctor.click();
    await doctor.first().click();
    await page
      .getByRole("option", { name: new RegExp(data.doctor) })
      .first()
      .click();
  }
  await p.getByRole("button", { name: "Save preauth draft" }).click();
  await expect(
    page.getByText("Pre-authorisation draft saved.").first(),
  ).toBeVisible();
  await e.step(
    "provider saves the pre-authorisation draft",
    `diagnosis ${data.diagnosis}, doctor ${data.doctor}`,
  );
  await attachDocuments(page, e);
  await answerForms(page, e);
}

const PDF = Buffer.from(
  "%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n" +
    "2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n" +
    "3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n" +
    "trailer<</Root 1 0 R>>\n%%EOF\n",
);

async function attachDocuments(page: Page, e: Entry) {
  const p = panel(page);
  const attach = p.getByRole("button", { name: "Attach chosen files" });
  if (!(await attach.isVisible().catch(() => false))) return;
  const card = p.locator("[data-slot=card]").filter({ has: attach });
  const rows = card.getByRole("row").filter({ hasText: /not attached yet/i });
  const n = await rows.count();
  const codes: string[] = [];
  for (let i = 0; i < n; i++) {
    const row = rows.nth(i);
    codes.push(
      ((await row.getByRole("cell").first().textContent()) || "").trim(),
    );
    await row.locator("input[type=file]").setInputFiles({
      name: `e2e-${codes[i] || i}.pdf`,
      mimeType: "application/pdf",
      buffer: PDF,
    });
  }
  if (!n) return;
  await attach.click();
  await expect(card.getByText(/not attached yet/i)).toHaveCount(0, {
    timeout: 30000,
  });
  await e.step("provider attaches the required documents", codes.join(", "));
}

async function answerForms(page: Page, e: Entry) {
  const p = panel(page);
  const card = p.locator("[data-slot=card]").filter({
    has: page.getByText("Forms the payer requires", { exact: true }),
  });
  if (!(await card.count())) return;
  const titles: string[] = [];
  const total = await card
    .locator("[data-state][data-orientation] > h3 button")
    .count();
  for (let i = 0; i < total; i++) {
    const trigger = card
      .locator("[data-state][data-orientation] > h3 button")
      .nth(i);
    titles.push(((await trigger.textContent()) || "").trim());
    if ((await trigger.getAttribute("aria-expanded")) !== "true")
      await trigger.click();
    const region = page.locator(
      `[id="${await trigger.getAttribute("aria-controls")}"]`,
    );
    await fillQuestions(page, region);
    await region.getByRole("button", { name: "Save answers" }).click();
    await expect(page.getByText(/Answers saved/i).first()).toBeVisible();
  }
  if (titles.length)
    await e.step(
      "provider answers the pre-authorisation forms",
      titles.join("; "),
    );
}

async function fillQuestions(page: Page, region: Locator) {
  const fields = region.locator("[id^=nhcx-q-]");
  const n = await fields.count();
  for (let i = 0; i < n; i++) {
    const f = fields.nth(i);
    const tag = await f.evaluate((el) => el.tagName.toLowerCase());
    const type = (await f.getAttribute("type")) || "";
    const role = await f.getAttribute("role");
    if (type === "file") {
      await f.setInputFiles({
        name: "e2e-form.pdf",
        mimeType: "application/pdf",
        buffer: PDF,
      });
    } else if (role === "combobox") {
      await f.click();
      const options = page.getByRole("option");
      await options.nth((await options.count()) > 1 ? 1 : 0).click();
    } else if (type === "date") {
      await f.fill(iso(new Date()));
    } else if (type === "datetime-local") {
      await f.fill(`${iso(new Date())}T10:00`);
    } else if (type === "number") {
      await f.fill("1");
    } else if (tag === "textarea" || tag === "input") {
      if (!(await f.inputValue())) await f.fill("e2e");
    }
  }
}

/** S9 send: the confirm button, then the dialog's Confirm. */
export async function sendPreauth(page: Page, e: Entry) {
  await openTab(page, "Pre-authorisation");
  const p = panel(page);
  const send = p.getByRole("button", { name: "Submit to payer" });
  await expect(send).toBeEnabled();
  await send.click();
  // only a resend or an enhancement asks to confirm
  const confirm = page.getByRole("button", { name: "Confirm", exact: true });
  if (
    await confirm
      .waitFor({ state: "visible", timeout: 3000 })
      .then(() => true)
      .catch(() => false)
  )
    await confirm.click();
  await page.waitForTimeout(3000);
  const red = await headerError(page);
  await e.check(
    !red,
    "provider sends the pre-authorisation",
    red || "sent",
    "ours",
  );
  await waitChip(
    page,
    e,
    "Pre-authorisation",
    ["Requested", "Approved", "Partially approved", "Queried", "Rejected"],
    "pre-authorisation goes out",
  );
}

/** The payer's decision through the shared payer driver (T2G). */
export async function payerDecides(
  e: Entry,
  claimId: string,
  stage: string,
  decision: string,
) {
  const record = backend<Record<string, unknown>>(
    "payer",
    "decide",
    claimId,
    decision,
    "--stage",
    stage,
    "--remarks",
    "e2e gui",
  );
  e.decisions.push(record);
  const trail = ((record.trail as { action?: string; role?: string }[]) || [])
    .map((s) => `${s.action} as ${s.role}`)
    .join(", ");
  if (record.skipped) {
    await e.step(
      `payer desk takes ${decision}`,
      String(record.skipped),
      "skipped",
    );
    return record;
  }
  const ok = ["decided", "completed"].includes(String(record.stopped));
  if (
    !ok &&
    /not enough cover left/i.test(trail + String(record.error || ""))
  ) {
    throw new Stop(
      `payer desk refuses ${decision}: the member's cover is used up (${trail})`,
      "blocked",
      "sandbox",
    );
  }
  await e.check(
    ok,
    `payer desk takes ${decision}`,
    `${record.stopped}, ${trail || record.error || ""}`,
    "sandbox",
  );
  return record;
}
