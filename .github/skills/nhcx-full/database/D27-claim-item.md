# D27. claim_item

#### D27T. TABLE
One row is one charge-master item on a non-package pre-authorisation draft: a fixed-price item and the quantity chosen. Primary key `id`. Parent table: `claim` (D9).

#### D27D. DESCRIPTION
A non-package case (`claim.case_type` `nonpackage`) is quoted item by item from the local charge master (D8 terminology kind `charge`, whose `extra` holds `price|type`).

**Written.** Only by saving the pre-authorisation draft (S4) with case type `nonpackage`, in the same transaction that replaces the claim's D25 and D26 rows: every D27 row of the claim is deleted, then the new items are inserted with `seq` 1, 2, 3 in order.

- An item whose code is not in the charge master is skipped.
- `code`, `display` and `unit_price` are re-read from the master at save time; the form supplies only the quantity.
- The quantity must be above 0 (a decimal is accepted here), otherwise the save is refused naming the item.
- `amount` is `unit_price * quantity`, rounded to 2 places.
- At least one item is required ("Add at least one item to a non-package case.").
- The claim's `preauth_total` becomes the sum of `amount`, rounded to 2 places.

Saving a `package` draft deletes every D27 row and inserts none.

**Read.** The draft card on S4 and S9 shows the saved items. The rows are not read by any bundle builder: the pre-authorisation and claim bundles quote the line items (D16), not these rows.

**Deleted.** On every draft save (replaced), by cascade with the claim, or when the transactional store is cleared. There is no status column.

#### D27C. COLUMNS
| Column | Type | Null / default | Meaning |
|---|---|---|---|
| id | INTEGER | primary key | Row id |
| claim_id | INTEGER | NOT NULL | The claim (D9) |
| seq | INTEGER | NOT NULL, default 1 | Order on the draft, from 1 |
| code | TEXT | NOT NULL | Charge master code (D8 kind `charge`) |
| display | TEXT | NOT NULL | Charge master name |
| unit_price | REAL | NOT NULL, default 0 | Fixed price from the master |
| quantity | REAL | NOT NULL, default 1 | Quantity chosen on the form |
| amount | REAL | NOT NULL, default 0 | `unit_price * quantity`, computed at save time |

#### D27K. KEYS AND INDEXES
- Primary key `id` (integer).
- Foreign key `claim_id` references `claim (id)` (D9), `ON DELETE CASCADE`.
- Index `ix_claim_item` on `(claim_id, seq)`.
- `code` is not a foreign key; it is copied from `terminology` (D8).

#### D27U. USED BY
- Screens: [S4. Claim Creation Form](../screens/S4-claim-creation-form.md)
- Database: [D8. terminology](D8-terminology.md), [D9. claim](D9-claim.md), [D18. claim_preauth](D18-claim-preauth.md), [D25. claim_diagnosis](D25-claim-diagnosis.md), [D26. claim_care_team](D26-claim-care-team.md)
