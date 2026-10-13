import { expect } from "@playwright/test";

import {
  Entry,
  addLine,
  backend,
  eligibility,
  fillDraft,
  login,
  nhcx,
  notDriven,
  openClaim,
  openTab,
  payerDecides,
  sendPreauth,
  testData,
  validate,
  waitChip,
} from "./helpers";

// PMJAY tests (T13..T19) through the screens. The package master is never
// waited for: it is seeded through the backend (T13), as the CLI runner does.

const NOT_DRIVEN =
  "GUI walk not written in this round; the CLI runner covers the scenario";

async function freeBeneficiary(e: Entry) {
  const out = backend("free-beneficiary");
  await e.step(
    "free the PMJAY beneficiary's open pre-authorisations",
    JSON.stringify(out).slice(0, 200),
  );
}

async function seed(
  page: import("@playwright/test").Page,
  e: Entry,
  claimId: string,
) {
  const out = backend<{ seeded: boolean; detail: string }>(
    "seed-plan",
    claimId,
  );
  await page.reload();
  await openTab(page, "Insurance plan");
  await expect(
    page.getByRole("tabpanel").getByText("Plan identifier"),
  ).toBeVisible();
  await e.step(
    out.seeded
      ? "package master seeded"
      : "payer's own package master is ready",
    out.detail,
  );
}

nhcx(
  "T13",
  "pmjay",
  "PMJAY Eligibility, Package Master and Ruling",
  async (page, e) => {
    await freeBeneficiary(e);
    await login(page, e);
    const claimId = await openClaim(page, e, "pmjay");
    await eligibility(page, e, "discovery");
    await eligibility(page, e, "validation");
    await seed(page, e, claimId);
    await addLine(page, e, testData().pmjay_package);
    await validate(page, e);
  },
);

nhcx(
  "T14",
  "pmjay",
  "PMJAY Pre-authorisation Through the Payer Service",
  async (page, e) => {
    await freeBeneficiary(e);
    await login(page, e);
    const claimId = await openClaim(page, e, "pmjay");
    await eligibility(page, e, "validation");
    await seed(page, e, claimId);
    await addLine(page, e, testData().pmjay_package);
    await validate(page, e);
    await fillDraft(page, e);
    await sendPreauth(page, e);
    await payerDecides(e, claimId, "preauth", "approve");
    await waitChip(
      page,
      e,
      "Pre-authorisation",
      ["Approved"],
      "PMJAY's decision arrives (C5)",
    );
  },
);

notDriven("T15", "pmjay", "PMJAY Query Answered by Resubmission", NOT_DRIVEN);
notDriven("T16", "pmjay", "PMJAY Rejection and Enhancement", NOT_DRIVEN);
notDriven("T17", "pmjay", "PMJAY Claim Through the Role Walk", NOT_DRIVEN);
notDriven(
  "T18",
  "pmjay",
  "PMJAY Payment Notice, Status Refusal and Cancel",
  NOT_DRIVEN,
);
notDriven(
  "T19",
  "pmjay",
  "PMJAY Beneficiary Verification and ABHA",
  NOT_DRIVEN,
);
