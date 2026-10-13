import {
  Stop,
  addLine,
  backend,
  eligibility,
  fetchPlan,
  fillDraft,
  login,
  nhcx,
  notDriven,
  openClaim,
  payerDecides,
  sendPreauth,
  testData,
  validate,
  waitChip,
} from "./helpers";

// IRDAI tests (T3..T12) through the screens. Shares the scenarios' test data
// and payer driver with the CLI runner (care/nhcx/tests/e2e).

const NOT_DRIVEN =
  "GUI walk not written in this round; the CLI runner covers the scenario";

function quoted(claimId: string, n = 1): string[] {
  const { codes } = backend<{ codes: string[] }>(
    "gui-lines",
    claimId,
    String(n),
  );
  if (codes.length < n)
    throw new Stop(
      `the plan lists ${codes.length} priced packages`,
      "blocked",
      "sandbox",
    );
  return codes;
}

nhcx("T3", "irdai", "IRDAI Policy Search and Eligibility", async (page, e) => {
  await login(page, e);
  await openClaim(page, e, "irdai");
  await eligibility(page, e, "discovery");
  await eligibility(page, e, "validation");
  const data = testData();
  await page.goto(
    `/facility/${data.facility}/claims/search?id_type=MemberId&id_value=${data.unknown_member}`,
  );
  await page.getByRole("button", { name: "Search policies" }).click();
  const none = page.getByText("No policy matches");
  const shown = await none
    .waitFor({ timeout: 60000 })
    .then(() => true)
    .catch(() => false);
  await e.check(
    shown,
    "unknown member id finds no policy",
    shown ? "No policy matches" : "results or an error shown",
  );
});

nhcx(
  "T4",
  "irdai",
  "IRDAI Insurance Plan and Authorisation Requirements",
  async (page, e) => {
    await login(page, e);
    const claimId = await openClaim(page, e, "irdai");
    await eligibility(page, e, "validation");
    await fetchPlan(page, e);
    const [code] = quoted(claimId);
    await addLine(page, e, code);
    await validate(page, e);
  },
);

nhcx("T5", "irdai", "IRDAI Pre-authorisation Approved", async (page, e) => {
  await login(page, e);
  const claimId = await openClaim(page, e, "irdai");
  await eligibility(page, e, "validation");
  await fetchPlan(page, e);
  const [code] = quoted(claimId);
  await addLine(page, e, code);
  await validate(page, e);
  await fillDraft(page, e);
  await sendPreauth(page, e);
  await payerDecides(e, claimId, "preauth", "approve");
  await waitChip(
    page,
    e,
    "Pre-authorisation",
    ["Approved"],
    "provider receives the approval",
  );
});

notDriven(
  "T6",
  "irdai",
  "IRDAI Pre-authorisation Rejected and Sent Again",
  NOT_DRIVEN,
);
notDriven("T7", "irdai", "IRDAI Query Answered", NOT_DRIVEN);
notDriven("T8", "irdai", "IRDAI Enhancement", NOT_DRIVEN);
notDriven("T9", "irdai", "IRDAI Status Enquiry and Cancel", NOT_DRIVEN);
notDriven(
  "T10",
  "irdai",
  "IRDAI Claim Approved, Part-approved and Rejected",
  NOT_DRIVEN,
);
notDriven(
  "T11",
  "irdai",
  "IRDAI Payment Notice and Acknowledgement",
  NOT_DRIVEN,
);
notDriven("T12", "irdai", "IRDAI Reprocess and Balance Release", NOT_DRIVEN);
