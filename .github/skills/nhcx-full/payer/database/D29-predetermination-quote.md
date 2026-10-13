# D29. predetermination_quote

#### D29T. TABLE
One row is one predetermination ("what would you pay for this"): the hospital's dossier as priced against the rules and answered, binding on nobody and opening no case; primary key `id`, ordered by `seq`. No parent table; the member and enrolment are named, not joined. The reference implementation names it `payer_predetermination_quotes` [REF](../references/PAYERS.md#markers).

#### D29D. DESCRIPTION
A predetermination is the one exchange this payer answers by rules rather than by a person ([C6. Predetermination](../callbacks/C6-predetermination.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md)). The Claim ([F8. Claim](../fhir/F8-claim.md), `use: predetermination`) is priced line by line against the member's product, and the answer ([F9. ClaimResponse](../fhir/F9-claimresponse.md)) goes out at once with the verdict and what would be allowed. Nothing on a case changes; the quote is filed here so the desk can show what was quoted (`GET quotes`, `GET quotes/:id`, listed on the case desk and the overview [REF](../references/PAYERS.md#markers)).

**Written** by [A10. Predetermination Quote](../apis/A10-predetermination-quote.md) after the answer is queued, with the whole request and response bundles, the findings the rules produced and the transaction the answer went out as. The correlation id is unique: a redelivered predetermination finds its quote rather than pricing twice, and [C6. Predetermination](../callbacks/C6-predetermination.md) answers it as a duplicate.

Verdicts, exact strings: `approve`, `partial`, `reject`, `query`. Findings are a JSON list, each with `rule_id`, `severity` (`reject`, `query`, `reduce`, `warn`), `path` (a locator into the Claim such as `Claim.item[2].net`), `sent`, `required`, `remedy`, and for a line finding `line_id` and `allowed`.

`scenario` records the sandbox preset the member id implied [SANDBOX](../references/PAYERS.md#markers).

Delete: never; the sandbox's clear-data removes a sign-up account's quotes [SANDBOX](../references/PAYERS.md#markers).

#### D29C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(24) | primary key | `QT-<random>` [REF](../references/PAYERS.md#markers) |
| seq | BIGINT | NOT NULL, identity, UNIQUE | insertion order |
| correlation_id | VARCHAR(128) | NOT NULL, UNIQUE | the thread the predetermination arrived on and was answered on |
| sender_code | CITEXT, at most 64 | NOT NULL | the hospital's participant code |
| claim_ref | VARCHAR(128) | null | the hospital's own number on the Claim |
| member_id | CITEXT, at most 48 | null | the member found ([D5. member](D5-member.md)) |
| subscription_id | VARCHAR(24) | null | the enrolment found ([D6. subscription](D6-subscription.md)) |
| patient_name | VARCHAR(160) | null | as the Claim named the patient |
| total_claimed | NUMERIC(14,2) | NOT NULL, default 0 | the sum of the lines sent |
| total_quoted | NUMERIC(14,2) | NOT NULL, default 0 | what the rules would allow |
| verdict | VARCHAR(16) | NOT NULL | `approve`, `partial`, `reject`, `query` |
| findings | JSONB | null | the rules' findings, as above |
| answer_txn_id | VARCHAR(128) | null | the ledger id the answer went out as |
| scenario | VARCHAR(40) | null | the sandbox preset played [SANDBOX](../references/PAYERS.md#markers) |
| request | JSONB | null | the Claim bundle as received |
| response | JSONB | null | the ClaimResponse bundle as sent |
| at | TIMESTAMPTZ | NOT NULL, default now | when |

#### D29K. KEYS AND INDEXES
- Primary key `id`. Unique `uq_quotes_seq` on `seq`; unique `uq_quotes_correlation` on `correlation_id`.
- Check `ck_quotes_codes_len` (`sender_code` at most 64, `member_id` at most 48).
- Index `idx_quotes_member` on `(member_id, at)`.

#### D29U. USED BY
- APIs: [A10. Predetermination Quote](../apis/A10-predetermination-quote.md)
- Callbacks: [C6. Predetermination](../callbacks/C6-predetermination.md)
- FHIR: [F8. Claim](../fhir/F8-claim.md)
- Tests: [T11. Predetermination Quoted](../tests/T11-predetermination-quoted.md)
