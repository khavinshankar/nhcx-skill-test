# S12. Organisation Screen

#### S12R. ROUTE
`/organisation`

| Endpoint | Purpose |
|---|---|
| `GET payer` | The insurer's record |
| `PATCH payer` | Save it |
| `GET participants/lookup?codes=a,b` | Name participant codes through the registry ([A17. Participant Lookup](../apis/A17-participant-lookup.md)) |

Not on the sidebar in the reference sandbox; reached by its route [REF](../references/PAYERS.md#markers). Breadcrumb: Organisation

#### S12D. DESCRIPTION
The insurer this deployment is ([D1. payer](../database/D1-payer.md)). Everything here ends up on the `Organization` resource of every bundle this payer issues ([F17. Organization](../fhir/F17-organization.md)), which is why it is a screen rather than a seed constant: a deployment that has not recorded its ROHINI id fixes that here, without a migration.

**1. Identity & Registries**: "The numbers a claim document identifies this insurer by. Each registry is separate, an IRDAI registration is not a ROHINI id, and neither is how the exchange addresses this payer."

| Field | Rule |
|---|---|
| Insurer Name | "Enter the insurer's name" |
| Payer Code, "This deployment's own label for the insurer" | "Enter the payer code"; goes on no wire |
| IRDAI Registration, "The insurer's registration number" | |
| ROHINI ID, "Registry of Hospitals in Network of Insurance" | |

**2. Exchange Identity**: "How NHCX addresses this payer. The registry issues these codes, so they are edited here rather than fixed at install, leave them blank and the deployment falls back to the codes it was configured with."

| Field | Rule |
|---|---|
| NHCX Participant Code, "Sent as `payerid`. The @hcx suffix is added if you leave it off." | optional; present, it must look like a participant code: "A participant code looks like `<payer code>`" |
| Processing Participant Code, "Sent as `processingid`. Only when a TPA adjudicates, blank means this payer." | the same |

The participant code is the `x-hcx-sender_code` of every answer and payer-started message ([G5. Protocol Headers](../gateway/G5-protocol-headers.md)) and the `payerid` of an ABHA link ([A16. ABHA Policy Link](../apis/A16-abha-policy-link.md)); the processing code is the `processingid`. The record wins over configuration: a payer that names its own code and no TPA processes its own claims, and a processing code left in configuration does not pair itself with it ([G2. Configuration and Participants](../gateway/G2-configuration.md)).

**Name the codes** [REF](../references/PAYERS.md#markers): the reference names participant codes through the registry ([A17. Participant Lookup](../apis/A17-participant-lookup.md)) in its participants dialog and the case list header, `{items: [{code, name, roles, status, found}]}`; a code the registry does not know comes back with `found` false rather than an error. A target may show the registry's name beside each code here.

**3. Contact & Address**: "Written as `telecom` and `address` on the Organization resource". Phone, Email ("Enter a valid email address"), Address, City, State, PIN Code, Country ("Enter the country", default India).

"Save Organisation" saves the whole record; toast "Organisation details saved". A deployment without a payer row: "This deployment has no payer record".

API: [A17. Participant Lookup](../apis/A17-participant-lookup.md)

Data: [D1. payer](../database/D1-payer.md)

#### S12L. LAYOUT
The arrangement below is the reference desk's [REF](../references/PAYERS.md#markers): follow the target payer system's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, the two participant codes and their rule.

```
|------------------------------------------------------------------|
| Issuing Organisation                                             |
| The insurer's own record, the Organization on every FHIR document|
|------------------------------------------------------------------|
| [Card] 1. Identity & Registries                                  |
|  Insurer Name [__________________________________]               |
|  Payer Code [SBXPAYER]  IRDAI Registration [____]  ROHINI ID [__]|
|------------------------------------------------------------------|
| [Card] 2. Exchange Identity                                      |
|  NHCX Participant Code [<payer code>]                            |
|  Processing Participant Code [________]                          |
|------------------------------------------------------------------|
| [Card] 3. Contact & Address                                      |
|  Phone [______]   Email [______]                                 |
|  Address [_________________________________]                     |
|  City [____] State [____] PIN Code [____] Country [India]        |
|------------------------------------------------------------------|
|                                             [(save) Save Organisation]|
|------------------------------------------------------------------|
```

- Three numbered cards, each with a title and a one-line description; one save button at the foot.
- Codes and registry numbers are monospace inputs with a hint line under each.

#### S12A. ACTIONS
1. Save Organisation: validate and save the record.
2. Edit any field: local until saved.
3. Name the codes (optional): look the codes up through the registry ([A17. Participant Lookup](../apis/A17-participant-lookup.md)) and show the names beside them.
