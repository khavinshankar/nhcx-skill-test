# Operations

What it takes to run the integration outside the sandbox: moving to production, and running the application as more than one instance. The go-live facts come from the knowledge source ([KNOWLEDGE.md](KNOWLEDGE.md)), which is the authority on them: `search_docs` for "going live" on the MCP, or `docs/07-Go Live/` in the package. This page is the checklist the build plans against; confirm every address and rule there before acting.

## Production cutover

### 1. Leave the sandbox
- Every exchange on the payer exit checklist is answered in the sandbox: L8 covers them (eligibility in every purpose, the plan, a pre-authorisation and its verdict, a rejection, an enhancement, a cancellation, a query and its answer, a claim and its verdict, a reprocess, the payment notices and their acknowledgement, a status enquiry, a predetermination). The sandbox provider EMR's own checklist for this payer's code shows what its traffic has proved [SANDBOX](PAYERS.md#markers).
- Sample FHIR bundles this payer sends (F3, F5, F9, F11, F13, F14) go to NHA for NRCeS validation, and the demos are given. Under PMJAY: the scheme's demo, the security audit and the sandbox exit form as well.

### 2. Production credentials
NHA confirms the certification and adds the payer role to the production client id. Where a separate participant processes the payer's claims (a TPA), its code is registered and mapped too. These go into the gateway configuration as secrets ([G2. Configuration and Participants](../gateway/G2-configuration.md)), never into the repository.

### 3. Register the participant again, in production
Four steps on the production participant service, each confirmed by a passcode sent to the registered mobile number (valid 24 hours; repeat a step whose passcode is lost):

1. Create the participant, with the payer's registered details as IRDAI holds them.
2. Confirm with the transaction id and passcode; the participant becomes active.
3. Update it with the production encryption certificate and the callback address (the `endpoint_url`), which is where every hospital's message will arrive.
4. Confirm again; the certificate and address go live.

Then fetch the payer's own certificate back from the production registry and check it matches the private key before anything is answered ([G4. Registry and Certificates](../gateway/G4-registry.md), [G11. Startup Checks and Health](../gateway/G11-startup-checks.md)). Hospitals encrypt to the certificate the registry holds: a stale one means nothing decrypts.

The gateway does not do these registry writes: certificate upload and endpoint updates are left out of it on purpose. They are done once, by hand or with the onboarding tool NHA provides.

### 4. Switch the addresses
Set the gateway's environment to production ([G2. Configuration and Participants](../gateway/G2-configuration.md)): it switches the NHCX base, the participant service, the sessions URL and the `X-CM-ID`. Some production addresses are published and the rest arrive with onboarding; hold every one in configuration, override any that differ, and confirm the session auth mode with the onboarding contact. The sandbox provider EMR and the sandbox scenarios ([A18. Provider Driver](../apis/A18-provider-driver.md), [A19. Sandbox Scenarios](../apis/A19-sandbox-scenarios.md)) are not used in production.

### 5. Open the network path
- The callback address is a domain name over HTTPS (TLS 1.2 or newer), hosted in India, with no IP address and no port in it.
- Allow NHCX's inbound addresses (listed in the go-live chapter of the knowledge source) to reach the inbound route ([G8. Receive](../gateway/G8-receive.md)). Every message from every hospital arrives through it; a closed door means silent hospitals and refused verdicts (NHCX-1010 once a correlation is retired).
- Run [G11. Startup Checks and Health](../gateway/G11-startup-checks.md) against production: token, registry record, certificate match and the endpoint probe must all pass.

### 6. Under PMJAY, the scheme's onboarding
The state health agency's own onboarding: the NHCX participant code is mapped to the scheme's payer record, and the hospitals it empanels are told the code to send to. Cases already open in the scheme's transaction system finish there.

### 7. Pilot, then switch
A few empanelled hospitals first, with the desk trained on the acknowledge-then-decide rhythm, then the whole book.

Record each of these as a step in `nhcx-plan/plan.json` (L3) with its owner, and log it in the progress log when done.

## Running more than one instance

The gateway keeps three kinds of state, and they behave differently across instances:

| State | Where | Across instances |
|---|---|---|
| Session tokens ([G3. Session Token](../gateway/G3-session-token.md)) and certificates ([G4. Registry and Certificates](../gateway/G4-registry.md)) | memory, per process | Safe. Each instance mints and caches its own; nothing is shared or persisted. |
| The ledger ([G9. Ledger](../gateway/G9-ledger.md)) as specified | files under the ledger directory, with indexes read into memory at startup | **Not shareable.** An instance reads the index files only when it starts, so it never sees entries another instance writes later, and each instance continues the day's id counter on its own, so two instances writing to one directory can mint the same ledger id. |
| The case tables (D) and the archive | the application's database and archive directory | Shared, as the rest of the application's data. |

G9 allows the ledger to live in the application's database instead of files, keeping the same contract. With the ledger in the shared database, every instance can answer, send and receive, and the rules below about one NHCX instance and its own ledger directory no longer apply; the idempotency rule still does.

With the file ledger as specified:

1. **One NHCX instance.** Exactly one instance holds the gateway: it mounts the inbound door, answers on the spot, sends and polls. Route NHCX's inbound traffic (`/in/...`, `/v1/...`) to it, and have the other instances (the desk the adjudicators use) hand outbound actions to it (a job queue or an internal call) rather than open a gateway of their own. A verdict taken on another instance is sent by this one.
2. **Its own ledger directory**, on storage that survives a restart. Never point two instances at one ledger directory.
3. **Idempotency lives in the database.** Every callback (C1 to C11) dedupes on the `api_call_id` recorded in [D28. nhcx_delivery](../database/D28-nhcx-delivery.md) and matches on the correlation ids and claim numbers stored on the case ([D19. case](../database/D19-case.md)), so a redelivery that lands after a failover opens no second case and files no document twice. Keep the unique keys the database specs name (for example on the pre-authorisation and claim correlation ids) so two concurrent deliveries cannot both insert.
4. **Failover** is a restart of the NHCX instance elsewhere with the same configuration, keys and ledger directory. Messages NHCX sent while it was down are redelivered (up to five attempts); a hospital's reply missed meanwhile is found by polling when the case is opened (A11, A12), because the ledger survives.
5. **The archive directory** may be shared; its writes are per case and append-only.

If the target cannot give one instance this role, record it as a risk in L3 with the mitigation chosen, since the gateway as specified does not coordinate between processes.
