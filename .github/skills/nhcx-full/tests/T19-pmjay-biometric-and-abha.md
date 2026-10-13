# T19. PMJAY Beneficiary Verification and ABHA

#### T19D. DESCRIPTION

The two ABDM calls beside the exchange, under the `pmjay` adapter ([PAYERS.md](../references/PAYERS.md)): the ABHA on the file put there by the ABHA service ([A19. ABHA Create and Verify (ABDM M1)](../apis/A19-abha-m1.md)), and the proof of presence the scheme reads off the request ([A18. Biometric Authentication](../apis/A18-biometric-authentication.md)). Three things are proved: a registration from a verified ABHA fills the file from the service's profile; a verified authentication puts the user token and the beneficiary's ABHA on the headers of the eligibility check ([A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md)) and the pre-authorisation ([A4. Pre-auth Submit](../apis/A4-preauth-submit.md)), and the consent questionnaire ([F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md)) is then **not** in the bundle; and with no token the bundle carries the Authentication Consent form answered, as every PMJAY send did before.

The sandbox cannot be driven through a fingerprint reader or a phone from a test runner, so the ABDM side is a stand-in in both runners [SANDBOX](../references/PAYERS.md#markers): a fake of the biometric hosts that answers init with a `txnId` and verify with a token pair, and a fake of the ABHA service that hands out a real RSA key, so the runner can open what the application sealed and check it. The exchange itself is real: the eligibility check and the pre-authorisation go to the PMJAY test payer, and what they carry is read back from the archive. A target with a registered device and a sandbox client id with M1 access may run the GUI against the real services; the expectations do not change.

#### T19S. SETUP

- [T1. Test Configuration](T1-test-configuration.md) and the PMJAY member id; the ABHA number the registry returns with the policy ([T13. PMJAY Eligibility, Package Master and Ruling](T13-pmjay-eligibility-and-package-master.md)).
- `NHCX_TEST_ABDM_FAKE=1` (default): the stand-ins for the biometric hosts and the ABHA service are started by the runner and the module's `biometric_base_url`, `faceauth_base_url` and `abha_base_url` point at them. Unset, the real sandbox hosts are used and the GUI run asks the operator to capture on the device and read the OTPs.
- `biometric_token_header` as the deployment sets it (default `x-hcx-user-token`).

#### T19G. GUI

1. [S13. Patient List](../screens/S13-patient-list.md) "Register with ABHA": verify by ABHA number, read the OTP, confirm the filled form and register; open [S15. Patient Detail](../screens/S15-patient-detail.md).
2. [S14. Patient Registration Form](../screens/S14-patient-registration-form.md) on a second patient: "Verify or create an ABHA", create from an Aadhaar OTP, pick an address, register.
3. [S1. Search Policy](../screens/S1-search-policy.md) and [S3. Policy Discovery](../screens/S3-policy-discovery.md): open a claim on the first patient's PMJAY policy and run the validation check **before** any authentication.
4. [S18. Beneficiary Verification](../screens/S18-beneficiary-verification.md), the Verification tab (stage Preauth, the patient admitted): fingerprint, capture (or paste the PID block), verify; the card reads "Verified, token live".
5. [S3. Policy Discovery](../screens/S3-policy-discovery.md): run the validation check again. [S8. Line Items](../screens/S8-line-items.md) quote a package, [S9. Pre-authorisation](../screens/S9-preauthorisation.md) send the pre-authorisation.
6. [S18. Beneficiary Verification](../screens/S18-beneficiary-verification.md) "Refresh token" after the token has lapsed (the stand-in issues a thirty-second token under the fake).
7. Discharge the admission ([S11. Claim Submission](../screens/S11-claim-submission.md)) and open [S18. Beneficiary Verification](../screens/S18-beneficiary-verification.md) again: it now reads "Discharge verification"; verify by face through the stand-in; the Aadhaar the application sent is opened with the ABHA service's key.

#### T19L. CLI

1. [A19. ABHA Create and Verify (ABDM M1)](../apis/A19-abha-m1.md) login OTP and verify by ABHA number; register the patient from the profile. [A19. ABHA Create and Verify (ABDM M1)](../apis/A19-abha-m1.md) enrol OTP, verify and address for the second patient.
2. [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md) validation on the claim, no authentication yet.
3. [A18. Biometric Authentication](../apis/A18-biometric-authentication.md) init (fingerprint), verify with a PID block; [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md) validation again; [A4. Pre-auth Submit](../apis/A4-preauth-submit.md) submit.
4. Advance the clock past the token (or wait); [A18. Biometric Authentication](../apis/A18-biometric-authentication.md) refresh; [A4. Pre-auth Submit](../apis/A4-preauth-submit.md) predetermination, which carries the refreshed token.
5. Discharge; [A18. Biometric Authentication](../apis/A18-biometric-authentication.md) init (face), capture, verify with an Aadhaar number; [A5. Claim Submit](../apis/A5-claim-submit.md) submit, which carries the discharge token and no Discharge Consent form.

#### T19X. EXPECT

- The first patient's file carries the ABHA number, address, name, gender, date of birth and mobile the ABHA service returned, and the second patient's `is_new` was true with the chosen address preferred. What the application sent to the ABHA service was sealed under its key: the runner opens `loginId` and `otpValue` and reads the digits back. No Aadhaar number, OTP or token appears in the audit trail, the archive or any API answer.
- The first validation check and its bundle carry no user-token header, and the bundle holds the Authentication Consent QuestionnaireResponse only where the master ships that form (it does on the PMJAY master).
- After the verify, the second validation check and the pre-authorisation go out with the user-token header set to the token the stand-in issued and `x-hcx-ben-abha-id` set to the beneficiary's ABHA; the pre-authorisation bundle carries no Authentication Consent QuestionnaireResponse. The init went to the biometric host with `Authorization` (not `bearer_auth`), `process` `Preauth`, `payerid` the scheme's identifier, and the ABHA **with hyphens**.
- The refresh replaces the token, and the next send carries the new one. A refresh with a lapsed refresh token is refused with "The refresh token has lapsed; authenticate the beneficiary again."
- [D31. biometric_auth](../database/D31-biometric-auth.md) holds every attempt with its method, transaction and `verified_at`; before the discharge the listing names the current one for stage `Preauth` and none for `Discharge`, after it one for each.
- The face verify's `aadhaar` opens under the ABHA service's key to the digits typed, the same key the M1 enrolment sealed the first patient's Aadhaar with; the claim goes out with the discharge token and `x-hcx-ben-abha-id`, and its bundle carries no Discharge Consent QuestionnaireResponse.
