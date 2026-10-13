# T3. IRDAI Policy Search and Eligibility

#### T3D. DESCRIPTION

The start of every IRDAI claim: the policy is found on the registry ([A1. Policy Search](../apis/A1-policy-search.md)) and the payer confirms it in force ([A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md), answered by [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md)). Discovery asks what cover the beneficiary holds; validation asks about the one policy chosen.

#### T3S. SETUP

- The IRDAI test payer and member id from [T1. Test Configuration](T1-test-configuration.md).
- A patient in the HMIS carrying that member id (create it through [S14. Patient Registration Form](../screens/S14-patient-registration-form.md) if the target has none, and reuse it after). The search is by **Member id**: the sandbox registry does not find this beneficiary by their ABHA number ([PAYERS.md](../references/PAYERS.md), "Sandbox participant codes") [SANDBOX](../references/PAYERS.md#markers).

#### T3G. GUI

1. [S5. Claim Master](../screens/S5-claim-master.md): start a new claim for the patient.
2. [S1. Search Policy](../screens/S1-search-policy.md): search by member id with the IRDAI test member id.
3. [S2. Select Policy](../screens/S2-select-policy.md): pick the policy the IRDAI test payer holds; the claim opens on [S6. Claim Detail](../screens/S6-claim-detail.md).
4. [S3. Policy Discovery](../screens/S3-policy-discovery.md): run discovery, wait for the verdict; then run validation on the chosen policy, wait for the verdict.
5. [S1. Search Policy](../screens/S1-search-policy.md) again with a member id no payer knows.

#### T3L. CLI

1. Open a claim for the patient through the service [S5. Claim Master](../screens/S5-claim-master.md) uses.
2. Call [A1. Policy Search](../apis/A1-policy-search.md) with the member id; pick the row whose payer is the IRDAI test payer.
3. Call [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md) with purpose `discovery`, wait for [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md) (T2 waiting rules); then with purpose `validation` and the chosen policy, wait again.
4. Call [A1. Policy Search](../apis/A1-policy-search.md) with an unknown member id.

#### T3X. EXPECT

- The search returns at least one policy of the IRDAI test payer. [S2. Select Policy](../screens/S2-select-policy.md) shows its payer; the processing id is read off the claim that "Select" opened ([S6. Claim Detail](../screens/S6-claim-detail.md), or the claim record in the CLI), and the claim is addressed to it (CORE confusions).
- Discovery and validation each go out (NHCX 202) and are answered on the same correlation id; [S3. Policy Discovery](../screens/S3-policy-discovery.md) shows the verdict and the policy's period and sum insured.
- An unknown member id comes back from the registry as "No policies found" (NHCX-1016); [A1. Policy Search](../apis/A1-policy-search.md) turns that into zero policies and [S2. Select Policy](../screens/S2-select-policy.md) shows "No policy matches that identifier." Not an error page, not a crash.
