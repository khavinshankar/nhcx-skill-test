# L7. Dry-run Tests

#### L7G. GOAL
Prove the code behaves as specified without touching NHCX or the ABDM registry. Everything outside the process is replaced: NHCX answers from a fake, the registry from fixtures, and inbound messages are fed straight to G8 and C1.

#### L7I. INPUTS
- `nhcx-plan/code.json`, `nhcx-plan/validation.json` (only validated files are tested).
- The test framework and command from discovery.json.

### L7.1 Set up the fakes
- A fake NHCX endpoint for G7 that records each request and answers 202, a non-2xx with an error body, or a transport failure, as the test asks.
- Registry fixtures for G4 (a participant record and certificate) and G10 (a policy search reply, and the "No policies found" error).
- A test key pair, so G6 encrypts and decrypts for real.
- A test database with the migrations applied.
- **The test process never opens the real gateway configuration or the participant's private key**, and never starts the gateway's loops (G1). A target that reads its environment file at start-up does this by accident: in the target's test settings pin the NHCX settings off, point the gateway at a throwaway configuration with a key pair generated for the run, add a loopback-only network guard (any connection to a host other than the fakes fails the test), use a temporary archive and ledger directory, and keep the tests off any shared cache or queue, so a developer's or CI's run can never send to NHCX or read another process's state.
- Received bundles taken from the knowledge source: `get_fhir_example` (MCP) or `nhcx-plan/knowledge/nhcx-package/fhir/` (package), copied into `tests/nhcx/fixtures/bundles/` with their source noted.

### L7.2 Test the FHIR mappers (F)
For each builder, build from fixture rows and check every FnF element and the F1 bundle order. Compare it element by element with the knowledge source's example bundle for the same exchange (`get_fhir_example`, or the package's `fhir/<use case>/` bundle); `validate_fhir` is not used on NHCX bundles ([KNOWLEDGE.md](../references/KNOWLEDGE.md)). For each parser, feed a bundle written from the FnF description and check the D columns it fills.

### L7.3 Test the APIs (A)
For each A, drive its pseudocode: every pre-send refusal (message verbatim), the successful send (the request G7 made, the D rows and statuses written), a send failure that names ids, and one that names none.

### L7.4 Test the callbacks (C)
For each C, hand an envelope to G8 (encrypted with the test key) or straight to C1, and check the result (`settled`, `unmatched`, `ignored`, `rejected`, `error`), the D changes, and the answer G8 gives. Include a redelivery and a `ProtocolResponse` for each.

### L7.5 Test the gateway (G)
Headers (G5), encryption round trip (G6), send result and error codes (G7), inbound refusal codes such as `WRONG_RECIPIENT` and `DECRYPT_FAILED` (G8), ledger queries and their order (G9).

### L7.6 Test the screens (S)
Render each screen with fixture data and check fields, options, columns, chips, empty states and validation messages; post each action and check where it leads.

### L7.7 Run the whole flow dry
One test walks a claim from S1 to S12 against the fakes: policy search, eligibility, plan, line items, pre-auth, a query and its reply, claim, payment and its acknowledgement.

#### L7O. OUTPUT
Test files in the target's test layout, and `nhcx-plan/dry-run.json`:

```json
{
  "command": "",
  "run_at": "<ISO time>",
  "tests": [
    {"file": "", "name": "", "covers": ["C5", "D18.status"], "result": "pass | fail | skip", "failure": ""}
  ],
  "coverage": {"S": [], "A": [], "C": [], "F": [], "D": [], "G": []},
  "summary": {"pass": 0, "fail": 0, "skip": 0},
  "corrections": []
}
```

#### L7L. LOG
Record in `nhcx-plan/progress.json` and regenerate `nhcx-plan/progress.md`, as [LOG.md](LOG.md) describes. One entry per sub-step, and one per test file created or modified, with the spec ids it covers. Each test run is logged with its pass, fail and skip counts, and every write to `nhcx-plan/dry-run.json`.

#### L7X. EXIT
- Every spec id in code.json `coverage` is covered by at least one passing test.
- The full dry flow (L7.7) passes.
- No test calls a real network address.
- Every sub-step of L7 has its `started` and closing entries in progress.json, and every file changed is named in one.
