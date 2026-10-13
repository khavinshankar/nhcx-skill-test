# T4. IRDAI Insurance Plan and Authorisation Requirements

#### T4D. DESCRIPTION

Before a pre-authorisation the provider needs the payer's package master ([A3. Insurance Plan Request](../apis/A3-insurance-plan-request.md), answered by [C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md)) and, for a payer that rules on it, what the chosen packages require ([A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md) with purpose `auth-requirements`, answered by [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md)). The IRDAI test payer's adapter rules on authorisation requirements ([PAYERS.md](../references/PAYERS.md)).

#### T4S. SETUP

A claim with the IRDAI test payer's policy chosen, as [T3. IRDAI Policy Search and Eligibility](T3-irdai-policy-and-eligibility.md) leaves it.

#### T4G. GUI

1. [S7. Insurance Plan](../screens/S7-insurance-plan.md): request the plan and wait until it is ready.
2. [S8. Line Items](../screens/S8-line-items.md): add a line from the plan's packages, with quantity and amount.
3. [S8.2](../screens/S8-line-items.md): ask the payer to validate; wait for the ruling.

#### T4L. CLI

1. Call [A3. Insurance Plan Request](../apis/A3-insurance-plan-request.md) for the claim's policy; wait for [C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md).
2. Add a line item for one of the returned packages through the service [S8. Line Items](../screens/S8-line-items.md) uses.
3. Call [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md) with purpose `auth-requirements` for the claim's lines; wait for [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md).

#### T4X. EXPECT

- The plan arrives `ready`, names the policy, and lists at least one package with its code and rate.
- The ruling arrives on the auth-requirements correlation id (not the eligibility one, CORE confusions) and lists the documents and forms each chosen package needs.
- [S8.2](../screens/S8-line-items.md) shows the ruling against each line, and the claim is ready for pre-authorisation.
