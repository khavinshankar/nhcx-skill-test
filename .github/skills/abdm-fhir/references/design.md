# Design an ABDM FHIR generator

What a bundle generator gets wrong before it reaches a profile table: reading one NRCeS source without the other, emitting a required child of an optional parent, and treating a bundle as a small object with a file attached.

## Read the profile and the example together, because each omits what the other carries

### In plain words

NRCeS publishes two things about every record type, and they answer different
questions. The profile gives the required elements and their cardinalities. The
example gives the shape, including values the profile never mentions.

Read alone, each one misleads. A generator written from the profile omits what
the example fills in. One written from the example hardcodes values the profile
never fixed. The only safe reading is both.

### What happens

Two places where the gap has teeth.

**The profile carries values a digest may not show you.** NRCeS fixes the
SNOMED CT code that types a Composition at `Composition.type.coding.code`,
three levels below the top of the resource, and the code is different for each
record type. `Composition.type.coding.system` is `http://snomed.info/sct`
wherever a code is used.

| Record type | `Composition.type.coding.code` | Where it is set |
|---|---|---|
| OPConsultation | `371530004`, Clinical consultation report | fixed by the OPConsultRecord profile |
| Prescription | `440545006`, Prescription record | fixed by the PrescriptionRecord profile |
| DischargeSummary | `373942005`, Discharge summary | fixed by the DischargeSummaryRecord profile |
| ImmunizationRecord | `41000179103`, Immunization record | fixed by the ImmunizationRecord profile |
| HealthDocumentRecord | `419891008`, Record artifact | fixed by the HealthDocumentRecord profile |
| DiagnosticReport | `721981007`, Diagnostic studies report | the example; the profile fixes the system only |
| WellnessRecord | no code; `Composition.type.text` is `Wellness Record` | the example |
| Invoice | no code; `Composition.type.text` is `Invoice Record` | the example |

Typing every document `419891008` is the commonest form of this mistake: it is
right for a HealthDocumentRecord only, and the [HI type](/docs/hiecm/v3/getting-started/glossary#hi-type)
a receiver reads from the bundle follows the code.

A summary that reports only the top two levels of a profile shows none of them,
and a reader concludes the code exists only in the example and is therefore
optional. Where the profile fixes it, it is not. Check the depth of whatever summary you
are reading before concluding something is absent.

**The example may use a shape the profile merely permits.** NRCeS requires
`Patient.identifier.type` and leaves `Patient.identifier.system` optional with
nothing prescribed, and its own code system carries `HIN` for the ABHA number
and `ABHA` for the ABHA address. No example uses either code. Every Patient in
the package instead carries:

| Identifier | `type.coding.code` | `type.coding.system` | `identifier.system` |
|---|---|---|---|
| ABHA number | `MR` | `http://terminology.hl7.org/CodeSystem/v2-0203` | `https://healthid.ndhm.gov.in` |
| Aadhaar | `ADN` | the NDHM identifier type code system | `https://uidai.gov.in/` |

Both satisfy the profile, because the binding on `identifier.type` is
extensible and `identifier.system` is free. They are not interchangeable to a
receiver reading by code. This catalogue documents the type code approach in
carrying an ABHA number and an ABHA address; what the
examples do is recorded here because the two differ and no source reconciles
them.

Neither reading has been confirmed against an ABDM receiver. Until one is,
carry both codes rather than choosing, and expect a receiver to select on
`type.coding.code`.

### How you know it worked

Take the record type you are producing. Open its digest and its example side by
side, and list every value in the example that the digest does not mention.
For a document Composition that list includes the SNOMED code, and each entry
is either a value the profile fixes at a depth your summary truncated, or a
convention the example is demonstrating.

Then generate a bundle and diff it against the example structurally: same
resource types, same nesting, same fixed values. A difference is either a
deliberate choice you can name, or a gap.

### When it goes wrong

- **A generated Composition has no `type.coding`.** It was written from a
  summary that truncated the profile before the fixed code.
- **A receiver cannot find the patient's ABHA number.** It selected on a code
  or a system your bundle does not carry. Carry both codes.
- **A value is hardcoded that the profile never fixed.** It came from the
  example alone. Check the profile before treating any example value as
  mandatory.

## A required child of an optional parent is a conditional requirement

### In plain words

A cardinality of `1..1` does not mean always send this. It means send exactly
one of these inside the thing that contains it, whenever that containing thing
is present.

So when the container is optional, the requirement is conditional. NRCeS has
three of these on every document Composition, and they catch people every time,
because a list of required elements reads like a list of things to emit.

### What happens

These three elements are `min: 1` on every ABDM record type:

| Element | Its own cardinality | Its parent | The parent's cardinality |
|---|---|---|---|
| `Composition.attester.mode` | 1..1 | `Composition.attester` | 0..* |
| `Composition.relatesTo.code` | 1..1 | `Composition.relatesTo` | 0..* |
| `Composition.relatesTo.target[x]` | 1..1 | `Composition.relatesTo` | 0..* |

NRCeS's own HealthDocumentRecord example carries neither an attester nor a
relatesTo. Both readings are correct: those cardinalities bind within the
parent, and the parent is optional. If you include an attester, it must carry a
mode.

A generator that reads `min: 1` as always emit produces an attester with no
party and a relatesTo pointing at nothing. That is worse than omitting both,
because the elements are now structurally present and semantically empty, and a
receiver cannot tell an unattested document from one attested by nobody.

The rule generalises past these three. Before emitting anything to satisfy a
required child, check whether its parent is required. This catalogue's profile
digests carry that answer: a required element whose nearest optional ancestor
exists names it in `optional_parent`, and an element with no `optional_parent`
is unconditional.

### How you know it worked

Ask for a profile digest and read the required list. Every entry that carries
an `optional_parent` is one you emit only when you are emitting that parent for
a reason of your own.

Generate a bundle for a document nobody attested. It contains no `attester` key
at all, rather than an attester carrying a mode and no party. Run it through the
validator and no message mentions `attester`.

### When it goes wrong

- **The validator complains about `Composition.attester.party`.** An attester
  was emitted to satisfy `attester.mode`. Remove the whole attester.
- **A `relatesTo` points at nothing.** Same cause. A relatesTo says this
  document replaces or appends to another one, so it needs a target that
  exists, and a document that relates to nothing omits the element.
- **A required element is missing and its parent is present.** The opposite
  mistake, and the one the validator does catch: once you include the parent,
  every `min: 1` inside it applies.

## Bundles are mostly somebody's health record, and they carry a narrative

### In plain words

A document bundle is not a small JSON object with a file attached. It is a file
with a small JSON object wrapped around it. NRCeS's own HealthDocumentRecord
example runs to 424,972 bytes and 417,032 of those are a single base64
attachment, so 98 per cent of what you are handling is the patient's document.

Everything awkward about storing, listing and logging these bundles follows
from that one number.

The second half of this atom is the part that is easy to skip, because nothing
fails without it: every resource carries a human readable narrative.

### What happens

**Do not put bundles in an index or a list document.** Store each one
separately and read it only when it is needed. An index rewritten on every
upload becomes unusable at a few dozen records.

**Never log the attachment.** It is a patient's record. It belongs in the
bundle and in the encrypted payload built from it, and nowhere else. A log line
that truncates it is still a log line containing part of it.

**Show a hash and a size instead**, so a file is identifiable in a list without
keeping a second copy of it.

Then the narrative. Every NRCeS example carries `text.div` on the Composition
and on each resource inside it. Skip it and the bundle still validates, and it
renders as machine output in a viewer built for people. Generate a plain
sentence naming what the document is and who it belongs to, and escape it,
because the inputs are a patient's name and a document title.

Two smaller conventions from the same examples, worth copying rather than
inventing:

| Convention | Value in the examples |
|---|---|
| `Bundle.meta.security` | confidentiality code `V`, very restricted |
| `Bundle.identifier.system` | the facility that minted the identifier |

Write the title for the patient. They read it in their own application months
later, not the receptionist filing it today.

### How you know it worked

Measure a generated bundle and the attachment inside it. The attachment is the
overwhelming majority of the bytes, which tells you the storage decision above
is the one that matters.

Open a generated bundle in a FHIR viewer built for people. Each resource shows
a readable sentence rather than a field dump.

Search your logs for a long base64 run. There is none.

### When it goes wrong

- **A list of records takes seconds to open.** Bundles are being held inside
  the list rather than stored separately.
- **A patient's document appears in a log or an error report.** The attachment
  was logged, which is a disclosure rather than a performance problem.
- **A viewer shows the record as raw fields.** No `text.div` was generated.
  Nothing failed, which is why it was missed.
- **A narrative renders as markup.** The patient's name or the document title
  was interpolated without escaping.

## Where these came from

- `shared.fhir.profile-and-example-together`
- `shared.fhir.conditional-cardinality`
- `shared.fhir.bundle-weight-and-narrative`
