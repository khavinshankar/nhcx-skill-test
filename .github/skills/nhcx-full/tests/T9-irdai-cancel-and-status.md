# T9. IRDAI Status Enquiry and Cancel

#### T9D. DESCRIPTION

A status enquiry and a cancel both go out as a Task ([A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md)). The IRDAI test payer answers a status enquiry ([C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md)) and a cancel ([C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md)) on `v1/task/on_submit`; the correlation id decides which (CORE confusions).

#### T9S. SETUP

Two claims with a pre-authorisation sent and still pending (no decision taken).

#### T9G. GUI

1. On the first claim, [S9. Pre-authorisation](../screens/S9-preauthorisation.md): ask for the status; wait for the answer.
2. On the second claim, [S9. Pre-authorisation](../screens/S9-preauthorisation.md): cancel the pre-authorisation with a reason; wait.
3. On the first claim, approve it through the payer driver, then try to cancel it on [S9. Pre-authorisation](../screens/S9-preauthorisation.md).

#### T9L. CLI

1. [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md) status on the first claim's leg; wait for [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md).
2. [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md) cancel on the second claim's leg; wait for [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md).
3. Approve the first claim's leg ([A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md), [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md)), wait for [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md), then [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md) cancel on it; wait for [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md).

#### T9X. EXPECT

- The status answer names the case's stage and is shown on [S9. Pre-authorisation](../screens/S9-preauthorisation.md) without changing the leg's status.
- The cancel is answered and the second leg ends `cancelled`.
- Where the payer refuses the cancel of a decided case, the first leg returns to the status it had before the cancel (`approved`), and the refusal is shown. Where the sandbox payer accepts it instead, record that as `skipped` for this check with the reason, never as a pass.
