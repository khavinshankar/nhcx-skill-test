# S11. FHIR Preview Screen

#### S11R. ROUTE
`/fhir`

| Endpoint | Purpose |
|---|---|
| `GET policies/:id/fhir?subscription_id=` | The product as an InsurancePlan bundle, with an enrolment's period and plan type when one is given |
| `GET subscriptions/:id/eligibility/fhir?case_id=&purpose=` | The enrolment as a CoverageEligibilityResponse bundle, narrowed by a case's asker and items when one is given |
| `GET cases/:id/fhir?kind=claimresponse&use=preauthorization|claim`, `kind=communicationrequest`, `kind=paymentreconciliation` | What this payer would send about a case now |
| `GET cases/:id/exchange`, `GET cases/:id/exchange/:msgId` | A message as it went over the wire, in either direction |

Breadcrumb: FHIR Preview

#### S11D. DESCRIPTION
A scratch console for the bundles this payer issues, and for the ones it received. It renders exactly what the builders in [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md), [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A5. Query Request](../apis/A5-query-request.md) and [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md) would send, with the rendering notes the builder attaches: what the desk's data could not supply. It writes nothing and sends nothing.

**Document kinds**, six buttons:

| Kind | Label | Profile (linked) | Note shown |
|---|---|---|---|
| plan | InsurancePlan | InsurancePlanBundle | "Bundle.type is fixed to `collection`, and InsurancePlan is 1..*, the Organization rides along as the `ownedBy` target." |
| eligibility | Coverage Eligibility | CoverageEligibilityResponseBundle | "Exactly one CoverageEligibilityResponse, plus everything it references, the Patient, the Coverage, the insurer, and the request being answered." |
| claimresponse | ClaimResponse | ClaimResponse | "The verdict as it stands: outcome and the claim-level `status` adjudication read together, one adjudicated item per line, the money under a `benefit` total." |
| communicationrequest | CommunicationRequest | CommunicationRequest | "The open query: one `payload[].contentString` per missing thing, `about` pointing at the Claim. The hospital answers with a Communication on the same correlation id." |
| paymentreconciliation | PaymentReconciliation | PaymentReconciliation | "Where the money is: a Task saying so, the PaymentNotice with the status, and the reconciliation with the UTR and the split between what was paid and the TDS withheld." |
| message | Exchange Message | Bundle | "A message as it went over the wire about this case, the Claim or Communication that arrived, or the verdict, query or notice that went out." |

**Selectors**, by kind:

- Policy Product (plan): every product; "No policies configured" when none.
- Enrolment (plan, eligibility): for a plan, only that product's enrolments, with "None, render the product on its own" ("supplies the cover period and plan type"); for eligibility, every enrolment ("whose cover is being asked about"), the first chosen by default. Options read "`<member>` · `<sub type>` · `<start>` to `<end>`".
- Case (eligibility: the member's own cases, "the hospital asking, and what about", with "None, a standing enquiry on the enrolment"; the case kinds: every case, those that came off the exchange first, "the case the document is about"). Options read "`<claim no>` · `<hospital>` · `<stage>` · `<hospital code>`".
- Message (message kind): the case's exchange log, "`↓ preauth · <time> · <summary>`" or "`↑ ...`", the newest chosen by default; "Nothing on the wire for this case" when empty.

Server refusals: "That enrolment is on a different policy", "That case belongs to a different member".

**Rendering notes**: each issue with its severity (error red, warning amber, info blue), its path and its message. A message recorded without its bundle shows the warning "This message was recorded without its bundle."

**Stats strip**: Bundle Type and Entries always; then for a case document Resource, Outcome (or status), Status (the claim-level adjudication reason, or the payment status), Amount (the `benefit` total or the payment amount), Items (items or payload entries); for a plan Coverage ("`<n>` groups / `<n>` benefits"), Doc Requirements, Sum Insured, Plan Type, Period; for eligibility In Force, Sum Assured (benefit[0] allowedMoney), Utilised (usedMoney), Balance (benefit[1] allowedMoney), Benefit Period, Outcome.

**The bundle**: two tabs, Resource Tree and Raw JSON, with "`<n>` lines · `<kb>` KB". Empty messages: "Choose a policy to render a bundle.", "Choose an enrolment to answer an eligibility enquiry.", "Choose a case that came off the exchange, and a message on it.", "Choose a case to render its document."; "Rendering…" while loading.

**Actions**: Regenerate, Copy ("Bundle copied to the clipboard", or "The browser refused clipboard access"), Download as `<profile>-<id>.json` with type `application/fhir+json`. The server answers the plan and eligibility renderings without escaping `<`, `>` and `&`, so a benefit comparator of `<=` is written as it stands [REF](../references/PAYERS.md#markers).

API: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md)

API: [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md)

API: [A3. Pre-auth Answer](../apis/A3-preauth-answer.md)

API: [A5. Query Request](../apis/A5-query-request.md)

API: [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md)

API: [A15. Case Exchange Log](../apis/A15-case-exchange.md)

Data: [D27. case_exchange_message](../database/D27-case-exchange-message.md)

#### S11L. LAYOUT
The arrangement below is the reference desk's [REF](../references/PAYERS.md#markers): follow the target payer system's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the kinds, the selectors, the notes and the two views of the bundle.

```
|------------------------------------------------------------------|
| FHIR Preview                  [Regenerate] [Copy] [(v) Download] |
| Render what this payer puts on the exchange ...                  |
|------------------------------------------------------------------|
| Document                                                         |
|  [InsurancePlan] [Coverage Eligibility] [ClaimResponse]          |
|  [CommunicationRequest] [PaymentReconciliation] [Exchange Message]|
|  Policy Product [Sandbox Default Policy (POL...) v]              |
|  Enrolment - supplies the cover period [None, render ... v]      |
|  (link) InsurancePlanBundle profile · Bundle.type is fixed ...   |
|------------------------------------------------------------------|
| Rendering notes                                                  |
|  (!) plan[0].period  No enrolment chosen; the period is left out |
|------------------------------------------------------------------|
| [Bundle Type collection] [Entries 3] [Coverage 6 groups / 14     |
|  benefits] [Doc Requirements 8] [Sum Insured ₹5,00,000] [Plan    |
|  Type Individual] [Period -]                                     |
|------------------------------------------------------------------|
| [Resource Tree] [Raw JSON]                       412 lines · 18 KB|
| +--------------------------------------------------------------+ |
| | { "resourceType": "Bundle", ...                              | |
| +--------------------------------------------------------------+ |
|------------------------------------------------------------------|
```

- The kind buttons are a row of toggles; the selectors sit under them in two columns; the profile link and note in one line beneath.
- The bundle view fills the rest of the page height, dark, with a tab bar above it.

#### S11A. ACTIONS
1. Pick a document kind: the selectors change to what that kind needs.
2. Pick a product, enrolment, case or message: the bundle re-renders.
3. Regenerate: render again from the current data.
4. Copy: the JSON to the clipboard.
5. Download: the JSON as a file.
6. Resource Tree / Raw JSON: switch the view.
