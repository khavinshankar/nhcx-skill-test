# Payers

NHCX standardises the envelope, not what a payer puts in it. Package codes, the workflow id each exchange travels under, how a payer asks a question, whether it rules on authorisation requirements: these differ by payer. The application keeps them in one place, a **payer adapter**, chosen per payer participant code, and the exchange code asks the adapter instead of hard-coding a scheme. This page is that one place.

## Markers

The specs mark every statement that is not the NHCX protocol itself:

| Marker | Means | What to do |
|---|---|---|
| [REF](PAYERS.md#markers) | A choice the reference implementation made (a layout, a label, an id format, a default). The protocol does not require it. | Follow it unless the target has a reason not to; record a different choice in `nhcx-plan/plan.json`. |
| [PAYER](PAYERS.md#markers) | Behaviour that depends on the payer adapter (for example a PMJAY rule or a workflow id). | Read the value from the adapter below, never hard-code it; check it against the knowledge source. |
| [SANDBOX](PAYERS.md#markers) | Something observed on the NHCX sandbox or a sandbox payer, not written in any specification. | Expect it in the sandbox; do not rely on it in production without confirming it. |

Unmarked statements are the protocol or this application's own design, and are followed as written. On the protocol the knowledge source ([KNOWLEDGE.md](KNOWLEDGE.md)) wins.

## Choosing the adapter

- A configuration row maps a payer's participant code to an adapter key: in the reference implementation, rows of kind `payer_adapter` in the code lists ([D8. terminology](../database/D8-terminology.md)), with the participant code as `code`, a label as `display` and the adapter key as `extra`. The row chooses the adapter and nothing else: **the payer's name shown anywhere is its registered name on the participant registry ([G4. Registry and Certificates](../gateway/G4-registry.md)), cached in the application**, never the row's `display`, the adapter's name, the search row's `payerName` or a configured default (registry names seen in the sandbox: `Sandbox Payer` for the IRDAI test payer, `SHA HP` for the PMJAY test payer). A payer whose registry lookup failed is shown by its code.
- The adapter is chosen by the policy's **payer id**. Messages are addressed to its **processing id** (the participant that handles the policy on NHCX), which can be a different code; see [CORE.md](CORE.md).
- Codes are matched on their numeric part, so `1518`, `1518@hcx` and `1518@HCX` are the same payer.
- A payer with no row is read by its **registered name** on the participant registry ([G4. Registry and Certificates](../gateway/G4-registry.md)): a name that starts with `SHA` (a State Health Agency, which runs the scheme) gets the `pmjay` adapter. The match ignores case and leading spaces. The name is learned from the payer list, or looked up once when the payer is first used and remembered; a lookup that fails is tried again after a few minutes.
- Every other payer with no row gets the **generic** adapter: a plain NRCeS bundle with none of any scheme's extras. A new payer therefore needs no configuration, and is never given the scheme's dialect unless its name says it is a State Health Agency. The claim screen names the adapter in use, so an unconfigured payer is visible.
- A configuration row always wins over the name.
- A workflow id missing from an adapter's table falls back to the PMJAY table's value for that kind; a kind no table defines is refused ("No workflow id is defined for '<kind>'.").

## The adapters

| Property | `pmjay` (PMJAY, State Health Agency) | `kyrocare` (Sandbox Payer) | `generic` |
|---|---|---|---|
| Payer code system | `https://payer.pmjay.nha.gov.in` | `https://kyro.care/fhir` | `https://nhcx.abdm.gov.in` |
| Programme code on every claim line | `AB-PMJAY` ("Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (AB-PMJAY)") | none | none |
| Authorisation requirements check (A2 `auth-requirements`, C3) sent on its own before a pre-authorisation or an enhancement | yes | yes | no (the reference implementation had it on for every adapter [REF](PAYERS.md#markers); a payer with nothing to say only slows the send) |
| Authorisation requirements check sent by the operator ("Validate procedure set") | allowed, optional | allowed, optional | allowed, optional |
| Document stages wanted at pre-authorisation | `pre` | `pre` | `pre` |
| Publishes a package master (A3, C4) | yes | yes | yes |
| Multiple-procedure factors (`Claim.item.factor`) | 1, 0.5, 0.25 (costliest in full, second at half, the rest at a quarter) | 1, 0.5, 0.25 | none |
| How it asks for more (query mode) | `resubmit`: the query is a ClaimResponse on the case's own thread, answered by submitting the leg again under the query-response workflow id; a CommunicationRequest from it is a notification, acknowledged, never answered | `communication`: a CommunicationRequest on a thread of its own, answered with a Communication (A7) | `communication` |
| Task input naming the case beside `claimNumber` (A6, F10), per kind | cancel: `initimationNumber`, the payer's own misspelling (`intimationNumber` is refused ERR-PYR-CLM-007) [SANDBOX](PAYERS.md#markers); reprocess: `intimationNumber` (`initimationNumber` was refused PAYR-1008) [SANDBOX](PAYERS.md#markers) | `intimationNumber` | `intimationNumber` |
| Answers a status enquiry (A6 status) | no: it refuses the Task (PAYR-1018, or PAYR-1008 with a reason code); read the case's state from its desk instead | yes | yes |
| Proof of presence (A18, S18) | required: the beneficiary's user token on the headers of the eligibility check, pre-authorisation and claim, else the Authentication Consent (questionnaire `100024`) answered in the pre-authorisation bundle and the Discharge Consent (`100466`) in the claim bundle; both are attachment questions (the signed declaration), so the desk uploads them on the leg's forms card, which offers the form whenever no token is held even when nothing lists it; refused by name without either (PAYR-1256, PAYR-1363) | optional: the token is sent when the desk has one, nothing stands in otherwise | optional, the same |
| Reprocess reason codes | `claimrejected`, `partialpayment`, `rejectiondisputed` | same | same |
| Adjudication desk (sandbox testing, A14, A15) | the NHCX Payer Service | the sandbox payer portal's own API | none |

The `kyrocare` adapter is the reference implementation's own sandbox payer portal; it speaks the PMJAY dialect for plans and rulings. Replace it with the payers the target actually deals with.

The authorisation requirements check is not a PMJAY feature and is not required of anyone. The operator may ask any payer for a ruling; a payer with nothing to say answers without one. No pre-authorisation waits for a ruling, and the adapter only decides whether the check also goes out unasked before a send.

## Workflow ids

The `x-hcx-workflow_id` each send travels under, per adapter, and the `x-hcx-status` NHA's workflow sheet pairs it with. An environment override may replace any workflow id. The status is set by the send: a query answer goes on a request path yet travels as `response.complete`, so the gateway's path default must not decide it (the reference implementation let it, sending `request.initiated` everywhere [REF](PAYERS.md#markers)).

| Send (kind) | `pmjay` | `kyrocare` | `generic` | API | `x-hcx-status` |
|---|---|---|---|---|---|
| Pre-authorisation (`preauth`) | 12 | 12 | 12 | A4 | `request.initiated` |
| Pre-auth resubmitted after a rejection (`preauth_resubmit`) | 121 | 121 | 121 | A4 (defined; the reference send logic never chooses it) | `request.initiated` |
| Pre-auth query answer (`preauth_query_response`) | 19 | 19 | 19 | A4 | `response.complete` |
| Enhancement (`enhancement`) | 13 | 13 | 13 | A4 | `request.initiated` |
| Enhancement query answer (`enhancement_resubmit`) | 131 | 131 | 131 | A4 | `response.complete` |
| Predetermination | 12 | 12 | 12 | A4 | `request.initiated` |
| Cancel (`cancel`) | PC01 | PC01 | PC01 | A6 | `request.initiated` |
| Claim (`claim`) | 15 | 15 | 15 | A5 | `request.initiated` |
| Claim resubmitted (`claim_resubmit`) | not offered: PMJAY refuses 16 with PAYR-1321 [SANDBOX](PAYERS.md#markers) | 16, not in NHA's published workflow list [REF](PAYERS.md#markers) | 16, not in NHA's published workflow list [REF](PAYERS.md#markers) | A5 | `request.initiated` |
| Claim query answer (`claim_query_response`) | 151, the published value, as the adapter default; the SHA sandbox refuses 151 and 19 with PAYR-1321 and takes 161, so a sandbox run sets 161 as a configuration override, never as the adapter's value [SANDBOX](PAYERS.md#markers) | 151 | 151 | A5 | `response.complete` |
| Payment acknowledgement (`payment_ack`) | 17 | the notice's own workflow id, echoed back | the notice's own workflow id | A8 | `response.complete` |
| Reprocess (`reprocess`) | 36 | 36 | 36 | A6 | `request.initiated` |
| Balance release (`release`) | 36 | 36 | 36 | A6 | `request.initiated` |

Eligibility checks (A2) and plan requests (A3) do not take their workflow id from this table. **The eligibility check (A2, every purpose) sends `11`** (Patient Admitted, NHA's own sample) by default, with a module setting (`eligibility_workflow_id`: `11` or `case`) to send the case number instead for a payer that wants it; both are accepted by the sandbox payers. **The plan request (A3) sends the case number** (the Task names no case, so this is how the exchange is found again) [REF](PAYERS.md#markers). A status enquiry sends the leg's own correlation id, else 13 [REF](PAYERS.md#markers). Confirm against the knowledge source (`workflow.yaml` in the package).

The payer's replies carry workflow ids of their own [PAYER](PAYERS.md#markers). The callbacks never route on them; they match on correlation ids. They do read them for the **status**: when a reply's `x-hcx-workflow_id` is one of the payer-side codes below, that code says what the reply is, and the bundle is read for the amounts and words only. A workflow id outside the list (a case number echoed back, for example) says nothing, and the bundle decides as [F9. ClaimResponse](../fhir/F9-claimresponse.md) describes.

| Reply workflow id | Leg status |
|---|---|
| 20, 25, 18, 251, 28, 29, 37 | `submitting`: received and under adjudication, an acknowledgement |
| 21, 22, 26, 252 | `approved` (`partial` when the bundle says the approval is partial) |
| 23, 231, 291, 253 | `rejected` |
| 24, 241, 27, 254 | `queried` |

An error wins over both: a reply with `x-hcx-status` `response.error`, a `ClaimResponse.error`, or an `error` outcome that is not a rejection is an error whatever its workflow id (see [F9. ClaimResponse](../fhir/F9-claimresponse.md)).

## Use case

Every pre-authorisation and claim send carries `x-hcx-use_case`, to every payer, whether or not the payer reads it. It is the same for all adapters.

| Send (kind) | `x-hcx-use_case` |
|---|---|
| `preauth`, predetermination, `claim` | `New` |
| `enhancement` | `Enhancement` |
| `preauth_resubmit`, `preauth_query_response`, `enhancement_resubmit`, `claim_query_response`, `claim_resubmit` | `Resubmit` |

## Sandbox participant codes

Seen in the reference implementation's sandbox runs [SANDBOX](PAYERS.md#markers). They are examples, not constants: a build reads every participant code from configuration.

| Code | Is |
|---|---|
| `1518@hcx` | the PMJAY (NHA) payer on the NHCX sandbox, adapter `pmjay` |
| `1000004805@hcx` | the reference implementation's IRDAI sandbox payer portal, adapter `kyrocare` |

What the sandbox registry finds [SANDBOX](PAYERS.md#markers): the IRDAI test beneficiary `MRAJ2004001` is found by **Member id** and not by the same person's ABHA number (`91-3333-2222-1111` returns no policy); a search by ABHA `91-7182-8065-4077` also returns no policy; and no search returns a beneficiary name (S2 shows "Unknown" by design, the name arrives with the eligibility verdict). A policy search started from the patient master ([S13. Patient List](../screens/S13-patient-list.md), [S15. Patient Detail](../screens/S15-patient-detail.md)) must therefore offer Member id beside the ABHA number and mobile.

## Test participants

The end-to-end tests ([TESTS.md](TESTS.md)) run against two payers. The values below are the defaults the test configuration ([T1. Test Configuration](../tests/T1-test-configuration.md)) starts from, except where the table says otherwise.

| Test payer | Participant code | Adapter | Adjudication desk (A14, A15) | Member id | Variable |
|---|---|---|---|---|---|
| IRDAI test payer | `1000004957@hcx` (Sandbox Payer NHA) | `kyrocare` | IRDAI payer desk (`irdai-payer`), fixed at `https://nhcxai.abdm.gov.in/uat/` (API at `/api/payer`), signed in to by token login | `MRAJ2004001` | `NHCX_TEST_IRDAI_PAYER`, `NHCX_TEST_IRDAI_MEMBER_ID` |
| PMJAY test payer | `1518@hcx` (PMJAY, NHA) | `pmjay` | NHCX Payer Service (`nhcx-payer-service`) | asked from the integrator, no default | `NHCX_TEST_PMJAY_PAYER`, `NHCX_TEST_PMJAY_MEMBER_ID` |

**The IRDAI payer desk is fixed.** It is not a setting and has no variable: its screens are at `https://nhcxai.abdm.gov.in/uat/`, its API at `https://nhcxai.abdm.gov.in/api/payer`. It is signed in to only by token login, with the facility's own ABDM session token (A14): there is no username, password or desk account to configure or ask for.

**PMJAY needs one value only the integrator has**: a PMJAY beneficiary's member id that the sandbox knows. It is asked from the integrator ([T1. Test Configuration](../tests/T1-test-configuration.md)), never guessed or taken from an example, and a PMJAY test without it is `blocked` with that reason. The beneficiary's ABHA number is not asked for: the registry returns it with the policy ([A1. Policy Search](../apis/A1-policy-search.md)). The facility's HFR id is not asked for either: it is the one on the facility's own record ([D1. organization](../database/D1-organization.md)), which every bundle already carries.

**PMJAY's package master is slow, may not arrive at all, and is never waited for.** The PMJAY sandbox has answered an insurance plan request ([A3. Insurance Plan Request](../apis/A3-insurance-plan-request.md)) in 15 to 60 minutes, and has also not answered within a whole session (requested at 20:23, still `fetching` after 50 minutes); meanwhile it refuses a second request for the same policy (PAYR-1406) [SANDBOX](PAYERS.md#markers). Nothing may depend on it: the tests request it once and move on, and run on a seeded package master instead ([T13. PMJAY Eligibility, Package Master and Ruling](../tests/T13-pmjay-eligibility-and-package-master.md)), which is the only source of PMJAY STG questions in a sandbox run. Note also that the knowledge package's PMJAY plan sample (`fhir/C4/C4-response-pmjay.json`) carries five plan questionnaires and **no** STG questionnaires, so neither the sample nor a late plan supplies them.
