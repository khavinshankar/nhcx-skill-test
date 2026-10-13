# A16. ABHA Policy Link

#### A16E. ENDPOINT

In-process: `registry.abha_link(body)` and `registry.abha_delink(body)`, [G10. Beneficiary Registry](../gateway/G10-beneficiary-registry.md), which post to the ABDM participant service with the session token ([G3. Session Token](../gateway/G3-session-token.md)): `POST {registry}/participant/link/abha/policy` and `POST {registry}/participant/delink/abha/policy` (NHA use cases `nha:C1` and `nha:C2`). Plain JSON, no JWE, no protocol headers, no ledger row.

Reached from the desk's own endpoints, behind a signed-in session with a payer desk role:

| Call | Does |
|---|---|
| `POST /subscriptions/:id/abha` | links the enrolment to an ABHA number |
| `DELETE /subscriptions/:id/abha` | removes the link |
| `GET /subscriptions/:id/abha/events` | the link and delink history, newest first |
| `GET /abdm/status` | whether a registry is reachable through the gateway, so the screen can say what linking will do before anybody presses it |

`:id` is the enrolment ([D6. subscription](../database/D6-subscription.md)).

#### A16D. DESCRIPTION

Linking puts an enrolment on the holder's ABHA account at the ABDM participant service, so the policy shows up in their health app and a hospital's policy search finds it by ABHA number. Delinking takes it off again. This is the payer's half of the beneficiary registry; the hospital's half is the policy search, which this payer never calls.

**Who the holder is.** The member on the enrolment, by member id, with the ABHA number typed on the screen (14 digits, separators stripped) and the mobile on the member record unless the screen gives another: ABDM finds the holder by either, and a policy sold against a mobile the member has since changed still has to be linkable. The product is the policy the member is enrolled on, by product id and name. The payer id and processing id are this payer's own participant code and its processing code ([D1. payer](../database/D1-payer.md); a TPA's when one processes the claims), sent explicitly so the call never claims that one participant insures the policy while another processes it.

**The request id is minted here**, not by the gateway: it is what ABDM's support desk asks for, and it has to be on the enrolment whether or not the call came back.

**No gateway, no pretence.** When no registry is configured the number is recorded on the enrolment with outcome `local` and the ABDM link status stays `none`: nothing outside this database has been told anything, and the enrolment does not claim otherwise. A delink of a link ABDM holds is refused without the gateway that made it.

**Every attempt is filed** ([D9. abha_link_event](../database/D9-abha-link-event.md)), whatever it did: a call ABDM refused writes the event and marks the enrolment's link status `failed`, and changes nothing else. The link it did not make is not half made.

**What the enrolment shows after a call** ([D6. subscription](../database/D6-subscription.md)):

| Action and outcome | `abha_linked` | `abha_no` | `abha_link_status` | `abha_linked_at` / `abha_delinked_at` |
|---|---|---|---|---|
| link, `success` | true | the number | `linked` | linked now |
| link, `local` | true | the number | `none` | unchanged |
| link, `failed` | unchanged | unchanged | `failed` | unchanged |
| delink, `success` | false | null | `delinked` | delinked now |
| delink, `local` | false | null | `none` | null |
| delink, `failed` | unchanged | unchanged | `failed` | unchanged |

The distinction between `abha_linked` (what this desk holds) and `abha_link_status` (what the exchange knows) is deliberate.

**Messages, verbatim.** "Enter the 14-digit ABHA number", "An ABHA number is 14 digits", "No subscription with that id", "This enrolment has no ABHA link to remove", "This ABHA is linked at ABDM. Configure the gateway to remove that link.", "ABDM refused the request: <message>" (502), "The gateway could not be reached: <message>" (504), "Recorded in the portal; no ABDM gateway is configured", "Removed in the portal; no ABDM gateway is configured".

Data: [D6. subscription](../database/D6-subscription.md), [D5. member](../database/D5-member.md), [D12. policy](../database/D12-policy.md), [D1. payer](../database/D1-payer.md), [D9. abha_link_event](../database/D9-abha-link-event.md), [D31. audit_log](../database/D31-audit-log.md).

#### A16Q. REQUEST

**From the desk**, `POST /subscriptions/:id/abha`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `abha_no` | string | yes | 14 digits; `91-8849-2019-4401` and `91884920194401` are the same number |
| `mobile` | string | no | the holder's mobile when it differs from the member record's |

`DELETE /subscriptions/:id/abha` takes no body.

**To G10**, the body of `registry.abha_link` and `registry.abha_delink`:

| Field | Type | Notes |
|---|---|---|
| `requestid` | string | a fresh UUID, minted here |
| `memberid` | string | the enrolment's member id |
| `abhanumber` | string | 14 digits; on a delink only when the enrolment still carries one |
| `mobilenumber` | string | bare digits |
| `payerid` | string | this payer's participant code |
| `processingid` | string | the processing code: a TPA's, else the payer's own |
| `policies[]` | list | `{"productid": <policy id>, "productname": <policy name>}` |

```json
{"requestid": "0b398fdf-0516-4935-9ebb-a0dc90a06bb6", "memberid": "MRAJ2004001",
 "abhanumber": "91884920194401", "mobilenumber": "9900112233",
 "payerid": "<payer code>", "processingid": "<payer code>",
 "policies": [{"productid": "POL7UMV001", "productname": "Sandbox Default Policy"}]}
```

A link needs an ABHA number or a mobile number; every call needs the member id and at least one policy. G10 refuses a body without them before any call.

#### A16S. RESPONSE

G10 returns the registry's status and body. The application keeps the line worth showing: ABDM's own `errormessage.errorcode: errordescription` when present, else the gateway's `error.message` or `message`, else "ABDM accepted the request".

**To the desk**, `200` with the enrolment ([D6. subscription](../database/D6-subscription.md)) as the screen shows it, after the attempt was filed. Errors: `422` for a bad number; `404`; `409` for the delink refusals; `502` "ABDM refused the request: <message>" when ABDM answered and refused; `504` "The gateway could not be reached: <message>" when nothing answered (worth retrying as it stands).

```json
{"id": "SUB-7UMV0042", "member_id": "MRAJ2004001", "policy_id": "POL7UMV001",
 "abha_linked": true, "abha_no": "91884920194401", "abha_link_status": "linked",
 "abha_request_id": "0b398fdf-0516-4935-9ebb-a0dc90a06bb6", "abha_linked_at": "2026-09-30T10:14:05.000Z"}
```

**The history**, `GET /subscriptions/:id/abha/events`, `200` `{"items": [{"id", "action", "outcome", "request_id", "http_status", "message", "response", "by", "at"}], "total": n}`, newest first. `http_status` is null when nothing answered.

**The status**, `GET /abdm/status`, `200` `{"configured": true, "gateway_url": "in-process"}`; `configured` is whether G10 has a registry URL for the environment ([G2. Configuration and Participants](../gateway/G2-configuration.md)).

#### A16P. PSEUDOCODE

When: the enrolment's "Link ABHA" and "Remove link" actions on [S5. Subscriptions](../screens/S5-subscriptions.md). Never on the exchange: a hospital's eligibility check reads the enrolment as it stands ([C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md)).

```text
LINK(id, abha_no, mobile, actor):
    canonical = digits of abha_no
    abha_no not blank                 or 422 "Enter the 14-digit ABHA number"
    len(canonical) == 14              or 422 "An ABHA number is 14 digits"
    sub = D6 by id, live              or 404 "No subscription with that id"
    if registry not configured (G2 has no registry URL):
        return FINISH(id, {action link, outcome local, abha_no canonical, token minted,
                           message "Recorded in the portal; no ABDM gateway is configured"}, "abha.linked.local")
    body = PAYLOAD(sub, canonical, mobile)
    result, err = registry.abha_link(body)                     # G10 -> nha:C1
    if err: return FAIL(id, "link", body.requestid, err, actor)
    return FINISH(id, {action link, outcome success, abha_no canonical, request_id, http_status result.status,
                       message result.message, response result.body}, "abha.linked")

DELINK(id, actor):
    sub = D6 by id, live              or 404 "No subscription with that id"
    if not sub.abha_linked and sub.abha_link_status != linked: 409 "This enrolment has no ABHA link to remove"
    if registry not configured:
        if sub.abha_link_status == linked: 409 "This ABHA is linked at ABDM. Configure the gateway to remove that link."
        return FINISH(id, {action delink, outcome local, message "Removed in the portal; no ABDM gateway is configured"}, "abha.delinked.local")
    body = PAYLOAD(sub, digits of sub.abha_no, "")               # the number only when still held
    result, err = registry.abha_delink(body)                   # G10 -> nha:C2
    if err: return FAIL(id, "delink", body.requestid, err, actor)
    return FINISH(id, {action delink, outcome success, request_id, http_status, message, response}, "abha.delinked")

PAYLOAD(sub, abha_no, mobile):
    member = D5[sub.member_id]        or 404 "The member on this subscription no longer exists"
    policy = D12[sub.policy_id]       or 404 "The policy on this subscription no longer exists"
    payer  = D1 (empty when unreadable: an unreadable record is not a reason to refuse a link)
    mobile = digits of (mobile or member.mobile)
    return {requestid: new UUID, memberid: sub.member_id, abhanumber: abha_no, mobilenumber: mobile,
            payerid: payer.nhcx_participant_id or configured code,
            processingid: payer.nhcx_processing_id or payer.nhcx_participant_id or configured processing code or configured code,
            policies: [{productid: policy.id, productname: policy.name}]}

FINISH(id, record, audit_action):
    in one transaction, enrolment locked:
        status = failed if record.outcome == failed
                 else linked if link and success, delinked if delink and success, else none
        write D6 per the table in A16D
        insert D9: subscription_id, action, outcome, request_id, http_status (null when 0),
                   message (cut to 500 characters), response, user
    audit (D31): audit_action, entity subscription, detail request_id
    return 200 D6[id]

FAIL(id, action, request_id, err, actor):
    file as FINISH with outcome failed, http_status err.status, message err.message, response err.body
    audit "abha.<action>.failed"
    if err is unreachable (no status): 504 "The gateway could not be reached: <message>"
    else:                              502 "ABDM refused the request: <message>"
```

#### A16U. USED BY
- Screens: [S5. Subscriptions](../screens/S5-subscriptions.md), [S12. Organisation](../screens/S12-organisation.md)
- APIs: [A20. ABHA Create and Verify (ABDM M1)](A20-abha-m1.md)
- Database: [D1. payer](../database/D1-payer.md), [D6. subscription](../database/D6-subscription.md), [D9. abha_link_event](../database/D9-abha-link-event.md)
- Gateway: [G1. Embedding](../gateway/G1-embedding.md), [G4. Registry and Certificates](../gateway/G4-registry.md), [G10. Beneficiary Registry](../gateway/G10-beneficiary-registry.md)
