# S5. Subscriptions Screen

#### S5R. ROUTE
`/subscriptions`

| Endpoint | Purpose |
|---|---|
| `GET subscriptions?search=&status=&policy_id=` | The enrolments |
| `POST subscriptions` | Enrol a member on a product |
| `GET subscriptions/:id`, `PATCH subscriptions/:id`, `DELETE subscriptions/:id` | One enrolment; edit; retire |
| `POST subscriptions/:id/status` | Pause or resume |
| `GET subscriptions/:id/wallet`, `POST subscriptions/:id/wallet` | The wallet ledger; a manual credit or debit |
| `POST subscriptions/:id/abha`, `DELETE subscriptions/:id/abha`, `GET subscriptions/:id/abha/events` | Link or delink the ABHA at ABDM; the attempts |
| `GET abdm/status` | Whether a gateway is configured, so the screen can say what linking will do |
| `GET terminology` | The plan-type value set |

Breadcrumb: Subscriptions

#### S5D. DESCRIPTION
An enrolment is one member on one product for one cover period, with a wallet: what is left of the sum assured this policy year ([D6. subscription](../database/D6-subscription.md)). It is what an eligibility check is answered from ([A1. Eligibility Answer](../apis/A1-eligibility-answer.md)): in force when active and today is inside the period, lapsed when the period has passed, and its wallet is the benefit the answer quotes. Approving a claim draws the approved amount down from it ([A13. Adjudicate](../apis/A13-adjudicate.md)); reopening the claim puts it back.

What NHCX adds to a screen most payer systems have: the cover period and status the exchange answers from, the wallet as the balance quoted, the plan type as an `ndhm-plan-type` code, and the **ABHA policy link**, which puts the enrolment on the holder's ABHA account at ABDM through the registry ([A16. ABHA Policy Link](../apis/A16-abha-policy-link.md), [G10. Beneficiary Registry](../gateway/G10-beneficiary-registry.md)) so it shows in their health app and a hospital's discovery check finds it.

**Cards**, one per enrolment: the member's name and the status (`active` green, `paused` amber); "Assigned Policy: `<product name>`"; "Cover: `<start>` to `<end>`"; "Total Wallet: ₹`<balance>`" and "Available: ₹`<balance less cases in payment>`" (the reference nets off approved cases in the payment stage in the browser [REF](../references/PAYERS.md#markers); the wallet balance on the server is already the truth); the ABHA status badge; and the actions "Link ABHA" or "Delink ABHA", "Pause" or "Resume", "Edit".

ABHA status badge, from `abha_link_status` and `abha_linked`:

| State | Label | Tone |
|---|---|---|
| `linked` | Linked at ABDM | green |
| `failed` | ABDM refused | red |
| `delinked` | Delinked at ABDM | muted |
| `none` with a number on file | ABHA on file, not sent to ABDM | amber |
| `none`, no number | No ABHA linked | muted |

Search matches the member's name, the product's name and the enrolment id. Empty states: "No subscriptions match" with "Nothing matches "`<term>`". Try a patient name or plan." and "Clear search"; "No subscriptions yet" with "Assign a policy product to a member to create their first subscription." and "Create subscription".

**Create / edit dialog**, "Create New Subscription" or "Edit Subscription `<id>`", sub-title "Link primary member, policy product, cover period, plan type, and add dependent members directly from Member Registry":

| Field | Control | Rule |
|---|---|---|
| Patient / Primary Member | select of members; fixed on edit | "Choose a member"; "No member with that id" |
| Assigned Insurance Policy | select of products, showing "(Base Sum: ₹x)"; fixed on edit; choosing one fills the wallet limit and plan type from the product | "Choose a policy"; "No policy with that id" |
| Cover Start Date, Cover End Date | dates | "Enter the cover start date", "Enter the cover end date", "The cover cannot end before it starts"; screen: "Cover cannot end before it starts" |
| Sold As (Plan Type) | select from the `ndhm-plan-type` value set ([D4. terminology_code](../database/D4-terminology-code.md)), "`<code>`, `<display>`" | required on edit: "Choose how this enrolment was sold" |
| Total Wallet Limit (₹) | number, the opening balance on create | "An opening balance cannot be negative" |
| Plan Type | two buttons: Individual, Family Floater | "Choose Individual or Family Floater" |
| Dependants (Family Floater only) | pick a member from the registry and a relation (Spouse, Child, Parent, Sibling), "Add Selected Dependent"; a list with "Remove Dependent" | "A family floater needs at least one family member"; each needs a name, relation, gender, date of birth; an ABHA number must be 14 digits and unique across the family: "Two family members cannot share an ABHA number" |

The member and the product are fixed once enrolled: re-pointing an enrolment would carry its wallet and claim history with it [REF](../references/PAYERS.md#markers). One member cannot be enrolled on the same product twice ([D6. subscription](../database/D6-subscription.md)). Toasts: "Subscription created!", "Subscription updated!". Screen refusal: "Please select both Member and Insurance Policy".

**Pause / Resume** posts `status` (`active` or `paused`: "A subscription is either active or paused") and toasts "Subscription paused" or "Subscription active". A paused enrolment is not in force ([A1. Eligibility Answer](../apis/A1-eligibility-answer.md)).

**Wallet dialog**, "Adjust Subscription Wallet": Credit (+) or Debit (-), Amount (₹). "Enter an amount greater than zero"; a debit below zero is refused, never clamped: "There is not enough cover left on this policy". Every movement writes a ledger row with the balance after it and the reason ([D8. wallet_entry](../database/D8-wallet-entry.md)); the reference reason reads "Manual credit from the subscriptions desk". Toast: "Wallet updated: ₹`<balance>`".

**ABHA Policy Link dialog**, sub-title "Link this enrolment's policy to the holder's ABHA account on ABDM, so it shows in their health app and a hospital's eligibility check can find it." It shows Policy Holder, Product, ABDM Status (the badge) and Request ID (the last call's `requestid`, which ABDM support asks for). Not linked: ABHA Number and Mobile Number ("ABDM finds the holder by either. It defaults to the number on the member record.") and the button "Link ABHA at ABDM", or "Record ABHA in the portal" when no gateway is configured. Linked: the number and "Delink ABHA", which asks once more as "Confirm, remove this link" with "The policy stops appearing on the holder's ABHA account, and the number is cleared here. The enrolment itself is untouched." A "Link History" lists every attempt, newest first: "`LINK` · accepted by ABDM" (or "refused", "recorded locally"), the time, the message, the request id and who.

Rules ([A16. ABHA Policy Link](../apis/A16-abha-policy-link.md)): "Enter the 14-digit ABHA number", "An ABHA number is 14 digits". With no gateway the number is recorded and the status stays `none`: toast "ABHA recorded in the portal, no ABDM gateway is configured"; a link ABDM acknowledged cannot be removed without the gateway: "This ABHA is linked at ABDM. Configure the gateway to remove that link." An enrolment with no link: "This enrolment has no ABHA link to remove". A refusal by ABDM changes nothing but the history: "ABDM refused the request: `<message>`" (502) or "The gateway could not be reached: `<message>`" (504). Success toasts: "ABDM linked this policy to the ABHA", "ABDM removed the link to this policy", "ABHA removed from the enrolment".

**Delete** retires the enrolment (soft); refused while cases refer to it.

API: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md)

API: [A13. Adjudicate](../apis/A13-adjudicate.md)

API: [A16. ABHA Policy Link](../apis/A16-abha-policy-link.md)

Callback: [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md)

Data: [D6. subscription](../database/D6-subscription.md)

Data: [D7. subscription_family_member](../database/D7-subscription-family-member.md)

Data: [D8. wallet_entry](../database/D8-wallet-entry.md)

Data: [D9. abha_link_event](../database/D9-abha-link-event.md)

#### S5L. LAYOUT
The arrangement below is the reference desk's [REF](../references/PAYERS.md#markers): follow the target payer system's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the period, status, wallet, plan type, family members and the ABHA link with its rules and messages.

```
|------------------------------------------------------------------|
| Subscriptions                            [(+) Create Subscription]|
| Manage subscriber policy assignments, wallet balances, statuses  |
|------------------------------------------------------------------|
| [(search) ______________________]      12 active subscriptions   |
|------------------------------------------------------------------|
| +---------------------+ +---------------------+ +---------------+|
| | Ramesh Kumar  ACTIVE| | Sita Devi     PAUSED| |               ||
| | Assigned Policy:    | |                     | |     ...       ||
| |  Sandbox Default    | |                     | |               ||
| | Cover: 2026-01-01 → | |                     | |               ||
| |        2026-12-31   | |                     | |               ||
| | Total Wallet ₹5,00,000                      | |               ||
| | Available    ₹4,31,000                      | |               ||
| | LINKED AT ABDM      | | NO ABHA LINKED      | |               ||
| | [Delink ABHA][Pause]      [Edit]            | |               ||
| +---------------------+ +---------------------+ +---------------+|
|------------------------------------------------------------------|
| Dialog: ABHA Policy Link                                         |
|  Policy Holder | Product | ABDM Status | Request ID              |
|  ABHA Number [______________]  Mobile Number [___________]       |
|  [Link ABHA at ABDM]                                             |
|  Link History: LINK · accepted by ABDM  2026-08-10 ...           |
|------------------------------------------------------------------|
```

- Cards in a four-column grid (fewer on smaller screens), each with a status word at the top right and the action bar at the bottom.
- The create dialog scrolls; the dependants block appears only for a family floater, with a registry picker, a relation select and the list of those added.
- The wallet dialog is small: two toggle buttons and one amount.
- The ABHA dialog is medium, with the summary grid, the form or the linked number, and a scrolling history.

#### S5A. ACTIONS
1. Create Subscription: open the dialog empty; save with "Create Subscription".
2. Edit: open the dialog with the enrolment's values (member and product fixed); save with "Save Subscription Changes".
3. Add Selected Dependent / Remove Dependent: build the family list before saving.
4. Pause / Resume: toggle the status.
5. Adjust wallet (the wallet dialog): credit or debit with a reason; a ledger row is written.
6. Link ABHA: open the ABHA dialog; "Link ABHA at ABDM" (or "Record ABHA in the portal") links through [A16. ABHA Policy Link](../apis/A16-abha-policy-link.md).
7. Delink ABHA: open the dialog; "Delink ABHA" then "Confirm, remove this link".
8. Search: narrow by member, product or id.
9. Delete: retire the enrolment.
