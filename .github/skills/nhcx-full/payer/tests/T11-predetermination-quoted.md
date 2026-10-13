# T11. Predetermination Quoted

#### T11D. DESCRIPTION

A Claim with use `predetermination` arrives on [C6. Predetermination](../callbacks/C6-predetermination.md) and [A10. Predetermination Quote](../apis/A10-predetermination-quote.md) prices it against the rules and answers at once: what the policy would allow, with the cuts. It binds nobody, opens no case, and a redelivery is quoted once.

#### T11S. SETUP

One member under the [T1. Test Configuration](T1-test-configuration.md) prefix enrolled on the default product with part of the wallet already used (a wallet adjustment on [S5. Subscriptions](../screens/S5-subscriptions.md)), so the quote shows a cut.

#### T11G. GUI

1. [S5. Subscriptions](../screens/S5-subscriptions.md): debit the enrolment's wallet by hand so less remains than the line will ask for; note the balance.
2. Hospital side, through the provider driver ([T2. Test Runners](T2-test-runners.md)): open a case, check eligibility, fetch the plan, add a line above the remaining cover, and ask for a quote.
3. [S2. Cases](../screens/S2-cases.md): no case has been opened.
4. [S1. Overview](../screens/S1-overview.md): the activity shows the quote answered; open the quotes list from it and read the quote: verdict, total claimed, total quoted, findings.
5. Hospital side: the predetermination card shows the amount the policy would allow.

#### T11L. CLI

1. Seed the member and enrolment; adjust the wallet through the desk's services.
2. Count the cases; through [A18. Provider Driver](../apis/A18-provider-driver.md), ask for the predetermination.
3. Read the quote through the quotes service ([A19. Sandbox Scenarios](../apis/A19-sandbox-scenarios.md) lists them) and the answer through [A12. Transaction FHIR](../apis/A12-txn-fhir.md); count the cases again.
4. Through [A18. Provider Driver](../apis/A18-provider-driver.md), deliver the same predetermination again.

#### T11X. EXPECT

- The delivery is answered `quoted` with `verdict` `partial` and `total_quoted` equal to what remains of the cover; the case count is unchanged; one row in [D29. predetermination_quote](../database/D29-predetermination-quote.md).
- The answer goes out on `v1/preauth/on_submit` on the asking correlation id, `response.complete`, a ClaimResponse with `use` `predetermination`, `outcome` `partial` and the allowed total under `benefit` ([F9. ClaimResponse](../fhir/F9-claimresponse.md)).
- The redelivery is answered `duplicate`; the answer went out once; still one quote.
- The hospital's side shows the quote answered with what would be allowed, and its pre-authorisation still unsent.
