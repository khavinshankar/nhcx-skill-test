# D32. id_sequence

#### D32T. TABLE
One row is one named id series and the next number in it; primary key `name`. No parent table. The reference implementation names it `payer_id_sequences` [REF](../references/PAYERS.md#markers).

#### D32D. DESCRIPTION
Business identifiers are the primary keys (a member id, a case id, a claim number, a payment number), because they are what an adjudicator reads out over the phone, and the database and the screen must agree on what a thing is called. They come from here rather than an identity column so the prefix and the width are decided in one place [REF](../references/PAYERS.md#markers).

A number is allocated with an update-and-return inside the transaction that inserts the row, which is atomic under concurrency in a way "max plus one" is not, and is rolled back with the insert if it fails rather than leaving a gap.

The series [REF](../references/PAYERS.md#markers):

| Series | Starts at | Used for |
|---|---|---|
| `member` | 1 | [D5. member](D5-member.md) `id`, `M<three letters><birth year><serial>` when no id is given |
| `policy` | 1001 | reserved; the reference numbers products from a per-day series `policy:<day code>` created on first use |
| `subscription` | 1 | [D6. subscription](D6-subscription.md) `id`, `SUB-<serial>` |
| `case` | 1001 | [D19. case](D19-case.md) `id`, `CASE-<serial>` |
| `claim` | 1001 | [D19. case](D19-case.md) `claim_no`, `CL/<yy>/<mmdd><serial>` in the sortable base32 alphabet |
| `payment` | 1 | [D30. payment](D30-payment.md) `id`, `PAY-<year>-<serial>` |

Policies, cases and claims start at 1001 so the first one issued does not look like a test row. A per-day series (`policy:<day code>`) is created on first use and cannot be seeded in advance.

Child rows that are never read out loud (line items, documents, doctors, timeline entries, messages, clauses, quotes) take short random ids, `<prefix>-<8 hex>`, which only have to be unique and short enough to sit in a URL [REF](../references/PAYERS.md#markers).

Delete: never.

#### D32C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| name | VARCHAR(32) | primary key | the series name |
| next_value | BIGINT | NOT NULL, default 1 | the next number to hand out |

#### D32K. KEYS AND INDEXES
- Primary key `name`.

#### D32U. USED BY
- Screens: [S4. Members](../screens/S4-members.md), [S10. Payments](../screens/S10-payments.md)
- APIs: [A14. Disburse](../apis/A14-disburse.md)
- Callbacks: [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)
- Database: [D5. member](D5-member.md), [D6. subscription](D6-subscription.md), [D19. case](D19-case.md), [D30. payment](D30-payment.md)
