# S17. Beneficiary Discovery Screen

#### S17R. ROUTE
claims/discovery

Optional query: `patient` (the patient the check is about) and `case` (the case to return the cover to).

Breadcrumb: Claims (claims/list, S5) > Discovery

Reached from the navigation ("Discovery", under Claims), from the policy search S1 when the registry finds nothing, and from the Eligibility tab S3.

#### S17D. DESCRIPTION
Discovery asks a payer directly who a person is to it: a coverage eligibility check with the purpose `discovery` ([A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md)). It has a page of its own because the request names the person by one identifier and the desk usually knows more than one thing about them. Whatever else it knows goes with the request as additional information, so the payer has more than one handle to match on.

The page is a stack of cards, in this order:
1. Patient
2. Discovery request
3. Cover returned (only once the payer has answered)
4. Discoveries sent (only when there are any)

**Patient card.** The patient picker until one is chosen; then the name, UHID, age and gender, mobile and ABHA number, with "Change patient" (hidden when the page was opened for a case).

**Discovery request card.**

| Field | Control | Default | Notes |
|---|---|---|---|
| Payer (required) | one typeahead over every payer on the exchange, government and private in one list | the only payer, when there is one | typing a name or a participant code narrows the list; there is no choice of payer kind first; a code typed in full that is not in the list is taken as typed |
| Search by (required) | dropdown: ABHA number, Mobile number, Member ID | ABHA number when the patient has one, else Mobile number | the identifier the request names the person by |
| Identifier value (required) | text | the patient's own value for the chosen kind | |

Then a block titled "Additional information", with the note "Sent with the discovery so the payer has more than one handle to match on. All optional.":

| Field | Control | Default | Rule |
|---|---|---|---|
| Aadhaar number | text, numeric | empty; never prefilled | 12 digits once spaces and hyphens are removed, else "An Aadhaar number has 12 digits" |
| Mobile number | text, numeric | the patient's mobile | 10 digits, else "A mobile number has 10 digits"; hidden when searching by mobile |
| Member ID | text | the patient's member id | hidden when searching by member id |

A field that repeats the identifier searched on is hidden and not sent.

Validation before anything is sent, each as a red message: "Select a patient first", "Choose the payer to ask", "Enter the <identifier> to ask about", then the two digit rules above.

API: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md) (purpose `discovery`, with the additional information)

FHIR: [F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md), [F15. Patient](../fhir/F15-patient.md) (the Aadhaar as an identifier typed `ADN`, the mobile as the phone, the member id as the member the bundle names)

**Waiting for the reply (async).** After a queued send the button gives way to "Waiting for <payer code> to answer" with the correlation id beneath it and "Stop waiting". The page polls for the reply every few seconds.

Callback: [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md)

**Cover returned card.** One tile per policy the payer returned: the product or payer name, the policy number and member id, then sum insured, valid until and status. No policy: "The payer answered with no cover for this person. Check the identifiers and ask again, or ask another payer." A refusal is shown as an error and stops the wait.

**Discoveries sent card.** Every discovery sent for the patient, newest first: the status chip (waiting, answered, failed), the payer code, the time, then the correlation id, the API call id and the transaction id, each copied on a click. Under them the additional information the request carried: Aadhaar (the last four digits only, as `XXXX XXXX 1234`), Mobile, Member ID. Opening a row shows the exchange legs.

Data: [D9. claim](../database/D9-claim.md)

#### S17L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, options, columns, statuses, messages and actions.

```
|------------------------------------------------------------------|
| Discovery                                             [< Back]   |
|------------------------------------------------------------------|
| [Card] Patient                                                   |
|  Asha Devi   <UHID> · 42y F · 98xxxxxx10 · ABHA 91-xxxx-xxxx-xx  |
|------------------------------------------------------------------|
| [Card] Discovery request                                         |
|  Payer *            [type a name or a participant code        ]  |
|  Search by *        [ABHA number v]   [91703412374240         ]  |
|  Additional information                                          |
|  Aadhaar number     Mobile number     Member ID                  |
|  [1234 5678 9012]   [98xxxxxx10  ]    [MD5SLS4X5   ]             |
|                                                 [Discover]       |
|------------------------------------------------------------------|
| [Card] Cover returned                                            |
|  [PMJAY for Himachal · PMJAY/HP/S/G · MD5SLS4X5 · active]        |
|------------------------------------------------------------------|
| [Card] Discoveries sent                                          |
|  Discovery [answered] <payer code> 12:00:05                      |
|  Correlation id ...   API call id ...   Transaction ...          |
|  Additional information  Aadhaar XXXX XXXX 9012  Mobile ...      |
|------------------------------------------------------------------|
```

#### S17A. ACTIONS
1. Discover: validate, open a draft case for the patient and payer when the page was not opened for a case (A2 `discover`: the facility guard is checked first, so a refusal creates no case), send the discovery (A2) on it with the additional information, and wait for the reply on this page.
2. Stop waiting: stop polling; the check stays in the list and can still be opened.
3. Choose a policy tile: fill the policy in on the case the discovery ran on (the draft case `discover` opened, or the case the page was opened for) and land on its Eligibility tab S3.
4. Back: to the case's Eligibility tab when the page was opened for a case, else to the claim list S5.
