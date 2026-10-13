# FHIR bundle fixtures

Example bundles from the NHCX reference package, `nha-in/nhcx-package` release
1.0.0, folder `fhir/`. Long base64 `data` values are cut to 40 characters, and
the two InsurancePlan replies are trimmed to a few categories, benefits and
questionnaires. Nothing else is changed.

| Fixture | Package source |
|---|---|
| eligibility-auth-request.json | fhir/B1/auth-requirements.json |
| eligibility-auth-response-pmjay.json | fhir/C3/C3-response-pmjay.json |
| eligibility-response-generic.json | fhir/C3/C3-response-generic.json |
| eligibility-benefits-response.json | fhir/C3/benefits-response.json |
| plan-response-generic.json | fhir/C4/C4-response-generic.json (trimmed) |
| plan-response-pmjay.json | fhir/C4/C4-response-pmjay.json (trimmed from 967 KB) |
| preauth-approved-wf21.json | fhir/C5/C5-approved-wf21.json |
| preauth-received-wf20-pmjay.json | fhir/C5/C5-received-wf20-pmjay.json |
| preauth-queried-wf24.json | fhir/C5/C5-queried-wf24.json |
| preauth-rejected-wf23-pmjay.json | fhir/C5/C5-rejected-wf23-pmjay.json |
| claim-approved-deduction-wf26-pmjay.json | fhir/C7/C7-approved-deduction-wf26-pmjay.json |
| claim-rejected-wf291.json | fhir/C7/C7-rejected-wf291.json |
| task-cancelled-wfPC02.json | fhir/C10/C10-cancelled-wfPC02.json |
| task-reprocess-wf37.json | fhir/C10/C10-arbitration-wf37.json |
| communication-query-wf24.json | fhir/C6/C6-preauth-query-wf24.json |
| communication-notification-wfN02-pmjay.json | fhir/C6/C6-notification-wfN02.json |
| payment-notice-wf30.json | fhir/C9/C9-notice-wf30.json |
| payment-notice-tds-wf30-pmjay.json | fhir/C9/C9-notice-tds-wf30-pmjay.json |
| claim-request-death-d9.json | fhir/D9/D9-request.json |
| payment-ack-b7.json | fhir/B7/B7-acknowledgement.json |
