# S18. Beneficiary Verification Screen

#### S18R. ROUTE
claims/view/:caseid/verification

The Verification tab of the Claim Detail shell S6, between Validate and Pre-authorisation. Its forms post to the application's biometric endpoints ([A18. Biometric Authentication](../apis/A18-biometric-authentication.md)) and the tab re-reads itself; nothing on it goes to NHCX.

Breadcrumb: Claims (claims/list, S5) > <case number> (S6)

#### S18D. DESCRIPTION
One card, "Beneficiary verification" while the patient is admitted and "Discharge verification" once the stay has ended. It proves the beneficiary is at the hospital by authenticating them against their ABHA ([A18. Biometric Authentication](../apis/A18-biometric-authentication.md)) and keeps the user token that results where the sends read it ([D31. biometric_auth](../database/D31-biometric-auth.md)). The tab is shown for every payer: any payer may be sent the token, and only a payer whose adapter requires proof of presence refuses a request without it ([PAYERS.md](../references/PAYERS.md)). A chip at the top says which: "Required by this payer" or "Optional for this payer".

**The stage follows the stay**, never a choice on the screen. While the linked admission is open, or the case has no admission yet, the authentication is stage `Preauth` (the scheme's process type `Preauth`): its token rides on the eligibility check ([A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md)) and the pre-authorisation ([A4. Pre-auth Submit](../apis/A4-preauth-submit.md)), enhancements and predeterminations included. Once the admission is discharged the tab turns into the discharge verification, stage `Discharge`: a fresh capture whose token rides on the claim ([A5. Claim Submit](../apis/A5-claim-submit.md)). The admission's token never serves the claim, whatever its life. On a cyclic case every visit is a Discharge-stage capture [PAYER](../references/PAYERS.md#markers).

**What the card says.** The current authentication for the patient, the payer and the stage ([D31. biometric_auth](../database/D31-biometric-auth.md), `current`): "Verified, token live" (green) with "by <method> at <time>, token until <time>" and a "Refresh token" button while the refresh token holds; "Verified, token lapsed" (amber) once the user token is gone and cannot be refreshed; or (amber) "Not verified: the consent questionnaire stands in on the send" for a payer that requires it, "Not verified: the sends carry no token" for one that does not.

**Authenticating.** Three method buttons, Fingerprint, Iris and Face, and "Authenticate the beneficiary" ("Authenticate again" when one exists), which starts an attempt at the stage of the stay with the ABHA on the policy, else the patient's.
- Fingerprint and iris open a capture panel: the method's instruction ("place the finger on the device"), a "Capture from the device" button that asks the RD service on this machine (ports 11100 to 11120, method `CAPTURE`, the `PidOptions` and the WADH of A18), a box to paste the PID block when the device is elsewhere, "Verify" (enabled once a PID block is present) and "Cancel".
- Face shows the QR code of the service's face-auth page for the transaction, "Scan the code with the ABHA app", and polls for the capture every few seconds ("Awaiting the capture..."). Once captured it asks the Aadhaar number ("sealed in this page under the ABHA service's certificate, never sent or stored in clear"; the page seals it with [A19. ABHA Create and Verify (ABDM M1)](../apis/A19-abha-m1.md)'s client and sends only the ciphertext) and the Aadhaar-linked mobile, then "Verify".
- Success: "Beneficiary verified by <method>" and the card re-reads. Failure: the service's words in red, and the attempt is listed as failed.

"Every attempt (n)" folds out the history: stage, method, status, time, transaction id, and the reason of a failed one. The card closes with the header the token rides under ("The user token rides on the exchange under `<header>` and never leaves the server").

Refusals are A18's, shown verbatim.

Data: [D31. biometric_auth](../database/D31-biometric-auth.md)

Data: [D3. patient](../database/D3-patient.md)

API: [A18. Biometric Authentication](../apis/A18-biometric-authentication.md)

#### S18L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS.

```
|------------------------------------------------------------------|
| [Card] Beneficiary verification                                  |
|  [Optional for this payer] [Verified, token live] by fingerprint |
|  at 10:32, token until 11:02            [(refresh) Refresh token]|
|  [Fingerprint] [Iris] [Face]        [Authenticate again]         |
|  ----------------------------------------------------------------|
|  Fingerprint: place the finger on the device                     |
|  [(fingerprint) Capture from the device]                         |
|  PID block from the RD service (pasted, when the device is       |
|  not on this machine)                                            |
|  [________________________________________________]              |
|  [(check) Verify]  [Cancel]                                      |
|  > Every attempt (3)                                             |
|  The user token rides on the exchange under x-hcx-user-token and |
|  never leaves the server.                                        |
|------------------------------------------------------------------|
```

- The face panel replaces the capture panel: the QR code on the left (about 9rem square, on white), the instruction and the waiting line beside it, then the Aadhaar and mobile boxes once captured.
- The method buttons are a small group; the chosen one is primary.

#### S18A. ACTIONS
1. Fingerprint / Iris / Face: choose the method.
2. Authenticate the beneficiary (or again): A18 init at the stay's stage; open the capture or face panel.
3. Capture from the device: read the RD service and fill the PID block.
4. Verify: A18 verify with the PID block, or the Aadhaar number and mobile for face; re-read the card.
5. Refresh token: A18 refresh on the current authentication.
6. Cancel: close the panel; the attempt stays listed as initiated.
7. Every attempt: fold the history out or away.
