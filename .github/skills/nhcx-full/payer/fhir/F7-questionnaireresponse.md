# F7. QuestionnaireResponse

#### F7R. RESOURCE
`QuestionnaireResponse`, received as entries of a hospital's Claim bundle ([F8. Claim](F8-claim.md)) on `v1/preauth/submit` and `v1/claim/submit`. No profile is checked. It is not filed in columns of its own: the answers are read out of the bundles the exchange log keeps ([D27. case_exchange_message](../database/D27-case-exchange-message.md)), so a case filed before the reader existed shows its answers too [REF](../references/PAYERS.md#markers). The desk reads them through [A15. Case Exchange Log](../apis/A15-case-exchange.md) (`GET cases/:id/forms`) and shows them on [S3. Case Desk](../screens/S3-case-desk.md).

#### F7D. DESCRIPTION
A payer's plan ships the forms it wants filled ([F6. Questionnaire](F6-questionnaire.md)): a treatment guideline per package, a consent. The hospital answers them on its own screen and each rides in the submission as a QuestionnaireResponse entry, which the Claim names on `supportingInfo` by reference. That reference is how the response is labelled: the reference's `display` is the form's title and its `category` says whether it is a treatment guideline (`STG`) or anything else (`INF`).

**Which responses count.** Every `QuestionnaireResponse` entry of the bundle, in bundle order. A response with nothing answered says nothing and is dropped: the hospital's builder never sends one, and one from elsewhere is not worth a card on the desk.

**Labelling.** The Claim's `supportingInfo[].valueReference.reference` is matched against the entry's `fullUrl`, else against `QuestionnaireResponse/<id>`. A response the Claim does not point at is still read; its title is then the last segment of its `questionnaire` url, or "Questionnaire".

**Flattening.** Items are walked with their nesting: a group heading is kept as a prefix, joined to the question with a middle dot, so two questions with the same wording under different groups stay apart. An answer's own follow-up items are read under the question they follow. A question with no `text` is named by its `linkId`.

**Values.** Whichever `value[x]` the answer carries. The hospital's builder writes `valueString` or `valueAttachment`; the rest are what a form answered elsewhere may hold and cost nothing to read:

| Answer element | Read as |
|---|---|
| `valueAttachment` | a document: `title` (else "Attachment"), `contentType`, and the size of the decoded body in bytes. The body itself is not copied out; it stays in the exchange log |
| `valueString`, `valueDate`, `valueDateTime`, `valueTime`, `valueUri` | the text as sent |
| `valueBoolean` | "Yes" or "No" |
| `valueInteger`, `valueDecimal` | the number, trailing zeros trimmed |
| `valueCoding` | the display, else the code |
| `valueQuantity` | the value and the unit, joined with a space |
| anything else | dropped |

An answer that yields neither a value nor an attachment is dropped.

**Where it shows.** One group per inbound submission that carried any form: the pre-authorisation, an enhancement or an answered query, the claim ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md)). Each group names the stage (`preauth` or `claim`, the exchange message's kind), the message id and when it arrived. A file given as a form answer is not also filed as a case document: it rides only inside the response.

#### F7F. FIELDS

| Element read | Stored in | Notes |
|---|---|---|
| `QuestionnaireResponse.questionnaire` | `forms[].questionnaire`; the title fallback | the Questionnaire url this payer published ([F6. Questionnaire](F6-questionnaire.md)) |
| `QuestionnaireResponse.status` | `forms[].status` | usually `completed` |
| `QuestionnaireResponse.authored` | `forms[].answered_at` | as sent |
| entry `fullUrl`, else `QuestionnaireResponse/<id>` | the key the Claim's pointer is matched on | |
| `Claim.supportingInfo[].valueReference.display` (matching pointer) | `forms[].title` | else the url's last segment, else "Questionnaire" |
| `Claim.supportingInfo[].category.coding[0].code` (matching pointer) | `forms[].category` | `STG` or `INF` |
| `item[].linkId` | `answers[].link_id` | `<code>/stg/<n>` for a treatment guideline this payer built |
| `item[].text` | `answers[].question` | the `linkId` when empty |
| the enclosing group's `text` chain | `answers[].group` | joined with a middle dot |
| `item[].answer[].value[x]` | `answers[].value`, or `answers[].attachment` (`title`, `content_type`, `bytes`) | table above |
| the whole bundle | [D27. case_exchange_message](../database/D27-case-exchange-message.md) `payload` of the inbound message | the only persistent record; nothing on [D19. case](../database/D19-case.md) or its children |

Nothing here decides anything: the answers are evidence for the adjudicator on [S3. Case Desk](../screens/S3-case-desk.md), read beside the documents ([D23. case_document](../database/D23-case-document.md)).

#### F7U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md)
- APIs: [A15. Case Exchange Log](../apis/A15-case-exchange.md)
- Callbacks: [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md)
- FHIR: [F6. Questionnaire](F6-questionnaire.md), [F8. Claim](F8-claim.md)
- Database: [D27. case_exchange_message](../database/D27-case-exchange-message.md)
