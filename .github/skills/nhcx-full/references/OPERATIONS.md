# Operations

What it takes to run the integration outside the sandbox: moving to production, and running the application as more than one instance. The go-live facts come from the knowledge source ([KNOWLEDGE.md](KNOWLEDGE.md)), which is the authority on them: `search_docs` for "going live" on the MCP, or `docs/07-Go Live/` in the package. This page is the checklist the build plans against; confirm every address and rule there before acting.

## Production cutover

### 1. Leave the sandbox
- Every case on the provider exit checklist passes in the sandbox (L8 covers the exchanges; cancel, reprocess, status and search are on the list).
- Sample FHIR bundles go to NHA for NRCeS validation, and the demos are given. Under PMJAY: the scheme demo, the security audit and the sandbox exit form as well.

### 2. Production credentials
NHA confirms the certification and adds the provider role to the production client id. Under PMJAY the production keys come on completion and serve private insurers too. These go into the gateway configuration as secrets ([G2. Configuration and Participants](../gateway/G2-configuration.md)), never into the repository.

### 3. Register the participant again, in production
Four steps on the production participant service, each confirmed by a passcode sent to the registered mobile number (valid 24 hours; repeat a step whose passcode is lost):

1. Create the participant, with the mobile number exactly as the HFR record holds it.
2. Confirm with the transaction id and passcode; the participant becomes active.
3. Update it with the production encryption certificate and the callback address (the `endpoint_url`).
4. Confirm again; the certificate and address go live.

In production the registry id is the facility's HFR id; sending the wrong one is a common failure. Then fetch the facility's own certificate back from the production registry and check it matches the private key before anything is sent ([G4. Registry and Certificates](../gateway/G4-registry.md), [G11. Startup Checks and Health](../gateway/G11-startup-checks.md)).

The gateway does not do these registry writes: certificate upload and endpoint updates are left out of it on purpose. They are done once, by hand or with the onboarding tool NHA provides.

### 4. Switch the addresses
Set the gateway's environment to production ([G2. Configuration and Participants](../gateway/G2-configuration.md)): it switches the NHCX base, the participant service, the sessions URL and the `X-CM-ID`. Some production addresses are published and the rest arrive with onboarding; hold every one in configuration, override any that differ, and confirm the session auth mode with the onboarding contact. The payer service used for sandbox adjudication is not used in production.

### 5. Open the network path
- The callback address is a domain name over HTTPS (TLS 1.2 or newer), hosted in India, with no IP address and no port in it.
- Allow NHCX's inbound addresses (listed in the go-live chapter of the knowledge source) to reach the inbound route ([G8. Receive](../gateway/G8-receive.md)).
- Run [G11. Startup Checks and Health](../gateway/G11-startup-checks.md) against production: token, registry record, certificate match and the endpoint probe must all pass.

### 6. Under PMJAY, the mapping ticket
Raise a ticket with the existing PMJAY hospital id, the TMS HEM id and the new NHCX participant code. NHA maps them by hand; that mapping is the switch. Cases already open in TMS finish in TMS.

### 7. Pilot, then switch
A few real cases first, with the desk trained, then the whole facility.

Record each of these as a step in `nhcx-plan/plan.json` (L3) with its owner, and log it in the progress log when done.

## Several desks on one participant

In the sandbox, and sometimes in production, several applications (desks) share one participant code: NHCX delivers every message for the code to the one registered `endpoint_url`, and a fan-out proxy in front of it posts the message to every desk and returns the **first** response it gets from any of them. Each desk then sees every message of every desk, and a slow or wrong answer from one desk is the answer NHCX records for all. The rules below keep a desk from spoiling another's exchange; [G8. Receive](../gateway/G8-receive.md) and [C1. Callback Door](../callbacks/C1-callback-door.md) implement them.

1. **A message this desk does not own ends `unmatched`, fast.** When no leg here waits on the correlation id and no case here carries the claim number, C1 answers `unmatched` without writing a row, without sending anything (C9 never acknowledges a notification it does not own, C10 never acknowledges a payment notice for a claim number it does not hold) and with only the `unmatched` archive entry. NHCX gets 202 at once.
2. **Never a non-2xx for a message that may be another desk's.** A 4xx or 5xx from this desk makes the proxy report failure for every desk. So a message that arrives while this desk's gateway is not open (configuration missing, keys not loaded, the application starting) is answered 202 `unmatched` on `/v1/...` and `/in/...`, not 503; only a message addressed to a code this desk hosts and that it cannot decrypt is refused as G8 says. Readiness is reported on `/readyz`, not by refusing NHCX.
3. **A ledger read failure is not a reason to refuse.** When `seen` or `last_inbound_request` ([G9. Ledger](../gateway/G9-ledger.md)) fails, the message is treated as not seen and goes on to C1; a failure is logged, never answered to NHCX.
4. **Claim-number prefixes differ per desk.** Payment notices and payer-started communications match on the claim number alone, so two desks minting `NM-...` numbers would claim each other's notices. The prefix of the claim series ([D30. counter](../database/D30-counter.md)) is a setting, set differently on every desk that shares a participant.
5. **Payer-side replies may reach every desk twice** (the proxy and NHCX's own redelivery); the dedupe rules of C1 hold.

## Running more than one instance

The gateway keeps three kinds of state, and they behave differently across instances:

| State | Where | Across instances |
|---|---|---|
| Session tokens ([G3. Session Token](../gateway/G3-session-token.md)) and certificates ([G4. Registry and Certificates](../gateway/G4-registry.md)) | memory, per process | Safe. Each instance mints and caches its own; nothing is shared or persisted. |
| The ledger ([G9. Ledger](../gateway/G9-ledger.md)) as specified | files under the ledger directory, with indexes read into memory at startup | **Not shareable.** An instance reads the index files only when it starts, so it never sees entries another instance writes later, and each instance continues the day's id counter on its own, so two instances writing to one directory can mint the same ledger id. |
| The claim tables (D) and the archive | the application's database and archive directory | Shared, as the rest of the application's data. |

G9 allows the ledger to live in the application's database instead of files, keeping the same contract. With the ledger in the shared database, every instance can send, poll and receive, and the rules below about one NHCX instance and its own ledger directory no longer apply; the idempotency rule still does.

With the file ledger as specified:

1. **One NHCX instance.** Exactly one instance holds the gateway: it mounts the inbound route, sends, and polls. Route NHCX's inbound traffic (`/in/...`, `/v1/...`) to it, and have the other instances hand NHCX actions to it (a job queue or an internal call) rather than open a gateway of their own.
2. **Its own ledger directory**, on storage that survives a restart. Never point two instances at one ledger directory.
3. **Idempotency lives in the database.** Every callback (C1 to C10) matches on correlation ids and `api_call_id`s stored in the claim tables and is safe to receive twice, so a redelivery that lands after a failover is harmless. Keep the unique keys the database specs name (for example on correlation ids) so two concurrent deliveries cannot both insert.
4. **Failover** is a restart of the NHCX instance elsewhere with the same configuration, keys and ledger directory. Messages NHCX sent while it was down are redelivered (up to five attempts); anything missed is found by polling when a case is opened (A10 to A13), because the ledger survives.
5. **The archive directory** may be shared; its writes are per case and append-only.

If the target cannot give one instance this role, record it as a risk in L3 with the mitigation chosen, since the gateway as specified does not coordinate between processes.
