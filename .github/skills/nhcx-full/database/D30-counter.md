# D30. counter

#### D30T. TABLE
One row is one named number series and the last value handed out from it. Primary key `name`. No parent table.

#### D30D. DESCRIPTION
**Created.** A series has no row until its first number is asked for. Allocation, in one write:

1. `INSERT INTO counter (name, value) VALUES (?, 0) ON CONFLICT (name) DO NOTHING`
2. `UPDATE counter SET value = value + 1 WHERE name = ?`
3. `SELECT value FROM counter WHERE name = ?`

The value returned is the new number, so the first number of any series is 1. The allocation runs under the application's write lock. Inside an open transaction it joins that transaction, so a write that fails and rolls back does not use up a number.

**Series in use** (`name`, and what the number becomes):

| name | Used for | Format |
|---|---|---|
| `claim` | claim numbers (D9 `claim_no`) | `NM-<yy>-<mmdd><serial>` [REF](../references/PAYERS.md#markers) |
| `mrn` | patient MRN (D3), when none is given; unused when the HMIS has its own patient identifier | `MRN` + 5 digits |
| `encounter_OPD`, `encounter_IPD` | visit and admission numbers (D4) | `OPD-` / `IPD-` + 5 digits |
| `lab` | lab orders | `LAB-` + 5 digits |
| `invoice` | invoices | `INV-` + 5 digits |
| `receipt` | receipts | `RCP-` + 5 digits |
| `appointment` | appointments | `APT-` + 5 digits |
| `dialysis_course`, `dialysis_session` | dialysis courses and sessions | `DLC-` / `DLS-` + 5 digits |
| `wellness` | wellness records | `WEL-` + 5 digits |

Other series are left-padded to 5 digits (wider numbers are not cut).

**Claim numbers.** The claim prefix (`NM` in the reference implementation [REF](../references/PAYERS.md#markers)) is a **setting**, not a constant: payment notices and payer-started communications are matched on the claim number alone, so every desk that shares a participant code must mint numbers under a prefix of its own ([OPERATIONS.md](../references/OPERATIONS.md)). Then the two-digit year, a hyphen, then 9 characters in a base32 alphabet whose ASCII order matches its numeric order (`0123456789ABCDEFGHIJKLMNOPQRSTUV`): 3 characters for month * 100 + day, and 6 for the next value of the `claim` series [REF](../references/PAYERS.md#markers). Example: `NM-26-0SE000001`, the first claim opened on 10 September 2026. Every number has the same length and sorts by date, then by issue order. The `claim` series never resets by date, so the serial keeps counting across days.

A claim number is taken when a claim is created from a selected policy (S2), and again when the payer accepts a pre-authorisation cancellation (C7) [REF](../references/PAYERS.md#markers): the withdrawn number stays on D18 `claim_ref` and the episode carries on under the fresh one.

**Updated.** Only by allocation (value + 1). Numbers are never handed back.

**Deleted.** Every row is deleted when the transactional store is cleared (the reset of patient data), so every series starts again at 1. Nothing else deletes rows.

#### D30C. COLUMNS
| Column | Type | Null / default | Meaning |
|---|---|---|---|
| name | TEXT | primary key | Series name (table above) |
| value | INTEGER | NOT NULL, default 0 | Last number handed out; 0 only between the insert and the first increment |

#### D30K. KEYS AND INDEXES
- Primary key `name`. No foreign keys, no other indexes.

#### D30U. USED BY
- Screens: [S2. Select Policy](../screens/S2-select-policy.md), [S9. Pre-authorisation](../screens/S9-preauthorisation.md)
- Callbacks: [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md)
- Database: [D9. claim](D9-claim.md), [D18. claim_preauth](D18-claim-preauth.md)
