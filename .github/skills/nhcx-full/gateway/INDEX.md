# Gateway

The NHCX gateway runs inside the application process, not as a separate service. It is the only part of the application that talks to NHCX and the ABDM registry: it holds the participant keys and session tokens, builds the protocol headers, encrypts and decrypts, dispatches, receives, and records every message in its ledger. APIs (A) and callbacks (C) call it in-process and refer to it by G number.

Only what the application needs is specified. Left out: the operator panel, terminal configurator, self-update, certificate generation and upload, registry endpoint updates, callback fan-out, and the payer-adjudicator relay (the payer service is called directly).

Each file has ENTRY (E), DESCRIPTION (D), INPUT (Q), OUTPUT (S), PSEUDOCODE (P) and USED BY (U) sections.

| # | Part | Entry | File |
|---|---|---|---|
| [G1](G1-embedding.md) | Embedding | `open`, `start`, mounted routes `/in/<path>`, `/v1/<rest>`, `/healthz`, `/readyz` | [G1-embedding.md](G1-embedding.md) |
| [G2](G2-configuration.md) | Configuration and Participants | config file, `${ENV}` and `@file` values | [G2-configuration.md](G2-configuration.md) |
| [G3](G3-session-token.md) | Session Token | `gateway.token`, `gateway.refresh_token`, `post_with_token` | [G3-session-token.md](G3-session-token.md) |
| [G4](G4-registry.md) | Registry and Certificates | `client.certificate`, participant lookup | [G4-registry.md](G4-registry.md) |
| [G5](G5-protocol-headers.md) | Protocol Headers | `build_protected_headers` | [G5-protocol-headers.md](G5-protocol-headers.md) |
| [G6](G6-encryption.md) | Encryption | `encrypt`, `decrypt`, `parse_header` | [G6-encryption.md](G6-encryption.md) |
| [G7](G7-send.md) | Send | `gateway.send(path, envelope)` | [G7-send.md](G7-send.md) |
| [G8](G8-receive.md) | Receive | `POST /in/<path>`, `POST /v1/<rest>` | [G8-receive.md](G8-receive.md) |
| [G9](G9-ledger.md) | Ledger | `ledger.related`, `ledger.fhir`, `ledger.dispatch`, `ledger.list`, `ledger.get` | [G9-ledger.md](G9-ledger.md) |
| [G10](G10-beneficiary-registry.md) | Beneficiary Registry | `registry.policies_search`, `abha_link`, `abha_delink` | [G10-beneficiary-registry.md](G10-beneficiary-registry.md) |
| [G11](G11-startup-checks.md) | Startup Checks and Health | `gateway.check`, `/healthz`, `/readyz` | [G11-startup-checks.md](G11-startup-checks.md) |
