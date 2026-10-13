# A1. Policy Search

#### A1E. ENDPOINT
In-process: `registry.policies_search({identifiertype, identifiervalue})`, [G10. Beneficiary Registry](../gateway/G10-beneficiary-registry.md). G10 posts it to the ABDM participant registry's Beneficiary Identification System, `POST {registry}/participant/get/policies`, with the G3 session token, and hands the registry's status and body back (synchronous).

#### A1D. DESCRIPTION
Beneficiary policy discovery. The operator types one identifier the beneficiary carries, and the app asks G10 for every policy linked to it. This is the first call of every new case and the only synchronous NHCX call in the workflow: no FHIR bundle, no JWE headers, no workflow id, no G9 ledger row, nothing archived.

G10 attaches the default participant's ABDM session token from [G3. Session Token](../gateway/G3-session-token.md) to the registry call, whichever facility asks. When the registry answers 401, G10 refreshes the token once and asks again, so a stale token does not reach the screen.

The app validates before calling:
- identifier type not one of the three below: "Choose what kind of identifier you are searching with."
- empty value after trimming: "Enter an identifier value to search for."

Identifier types, in the order offered (Member ID is the default because it is printed on the beneficiary's card and the payer's directory is keyed on it) [REF](../references/PAYERS.md#markers):

| `identifiertype` | Label |
|---|---|
| `MemberId` | Member ID |
| `MobileNo` | Mobile number |
| `AbhaNumber` | ABHA number |

#### A1Q. REQUEST

The arguments passed to G10, sent to the registry as this JSON body:

| Field | Type | Required | Value |
|---|---|---|---|
| `identifiertype` | string | yes | `MemberId`, `MobileNo` or `AbhaNumber` |
| `identifiervalue` | string | yes | the identifier, trimmed |

```json
{"identifiertype": "MemberId", "identifiervalue": "MD5SLS4X5"}
```

#### A1S. RESPONSE
G10 hands the BIS reply back verbatim as `{status, body}`: the registry's HTTP status and its JSON body (a non-JSON body as `{"error": "<text>"}`). The observed sandbox reply is a top-level array [SANDBOX](../references/PAYERS.md#markers):

```json
[{"abhanumber": "91703412374240", "memberid": "MD5SLS4X5",
  "mobilenumber": "", "payerid": "<payer code>", "processingid": "<payer code>",
  "productid": "PMJAY/HP/S/G", "productname": "PMJAY for Himachal",
  "sno": "200013271"}]
```

How the reply is read:
- A list is taken as the rows. An object is read from its `policies`, `result` or `data` key, the first non-empty one. Anything that is not a list of objects is zero policies.
- Each row is normalised onto one vocabulary, first non-empty source field wins, and the untouched row is kept as `raw`:

| Normalised | Source fields, in order |
|---|---|
| `member_id` | `memberid`, `member_id`, `memberId`, `pmjayid` |
| `name` | `name`, `membername`, `patient_name`, `patientName`, `beneficiaryname`, `beneficiaryName` |
| `policy_code` | `policy_number`, `policyNumber`, `policyno`, `policyNo`, `policycode`, `productid` |
| `payer_id` | `payerid`, `payerId`, `insurer_code` |
| `processing_id` | `processingid`, `processingId`, `processingID`. The participant that processes the policy on NHCX, which may differ from the payer (for example a state health agency or a TPA). It is the `x-hcx-recipient_code` of every exchange on the case; the payer id only picks the payer adapter. Using the payer id as recipient is refused with NHCX-1003 (receiver not registered). |
| `payer_name` | **not read from the row.** The payer's registered name is fetched from the participant registry ([G4. Registry and Certificates](../gateway/G4-registry.md)) by `payer_id` when the row is shown (S2) and when the case is opened (D9), and cached; the row's own `payerName` / `payername` / `insurer_name`, a configuration label, the adapter's name and any default name are never used. A payer whose lookup failed is shown by its code |
| `product_id` | `productid`, `productId` |
| `product_name` | `productname`, `productName` |
| `abha_number` | `abhanumber`, `abhaNumber`, `abha_number` |
| `mobile_number` | `mobilenumber`, `mobileNumber`, `mobile` |
| `photo` | `photo`, `photoUrl`, `beneficiaryphoto`, `memberphoto` |

- The sandbox carries the plan identifier in `productid`, which is why it is the last fallback for `policy_code` [SANDBOX](../references/PAYERS.md#markers).
- The sandbox returns no beneficiary name and no photo at this stage; both arrive later with the eligibility verdict (A2) [SANDBOX](../references/PAYERS.md#markers).

Errors:
- Nothing linked to the identifier comes back from the registry as HTTP 400 with code `NHCX-1016`. The app recognises it by the text `No policies found` in the registry's error message and returns zero policies, not an error.
- Any other failure (a registry `status` outside 2xx, a G10 error such as an unreachable registry or no session token) is a red error card on the screen.

#### A1P. PSEUDOCODE

```
function search_policies(id_type, id_value):
    // pre-send checks
    if id_type not in {MemberId, MobileNo, AbhaNumber}:
        refuse "Choose what kind of identifier you are searching with."
    id_value = trim(id_value)
    if id_value is empty:
        refuse "Enter an identifier value to search for."

    // the call (in-process, synchronous; no bundle, no headers, no ledger row, nothing archived)
    try:
        answer = registry.policies_search({identifiertype: id_type,     // G10, registry
                                           identifiervalue: id_value})  // participant/get/policies
        if answer.status not 2xx: raise registry error, message read from answer.body
        reply = answer.body
    catch registry_error or g10_error:
        if its message contains "No policies found":             // NHCX-1016
            return []                                            // zero policies, not an error
        raise it                                                 // red error card

    // reading the reply
    if reply is a list:        rows = reply
    else if reply is an object: rows = first non-empty of reply.policies, reply.result, reply.data, else []
    else:                      rows = []
    if rows is not a list:     rows = []

    return [normalise(row) for row in rows if row is an object]

function normalise(row):
    // first non-empty source field wins (table above)
    payer_name = registry_name(payer_id)          // G4 participant fetch, cached; null when the lookup failed
    return {member_id, name, policy_code, payer_id, processing_id, payer_name, product_id,
            product_name, abha_number, mobile_number, photo, raw: row}
```

Data: [D9. claim](../database/D9-claim.md) (where the selected row is stored)

#### A1U. USED BY
- Screens: [S1. Search Policy](../screens/S1-search-policy.md), [S2. Select Policy](../screens/S2-select-policy.md)
- APIs: [A2. Coverage Eligibility Check](A2-coverage-eligibility-check.md)
- FHIR: [F15. Patient](../fhir/F15-patient.md), [F18. Coverage](../fhir/F18-coverage.md)
- Database: [D9. claim](../database/D9-claim.md)
- Gateway: [G1. Embedding](../gateway/G1-embedding.md), [G10. Beneficiary Registry](../gateway/G10-beneficiary-registry.md)
- Tests: [T3. IRDAI Policy Search and Eligibility](../tests/T3-irdai-policy-and-eligibility.md), [T13. PMJAY Eligibility, Package Master and Ruling](../tests/T13-pmjay-eligibility-and-package-master.md)
