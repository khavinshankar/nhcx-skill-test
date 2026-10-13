# Insurance plan not received for NM-26-0VL00003S — investigation

Session: afb9f59a-c984-46a8-83b1-fc23c81a1f78 (question-only; no code changed)

## Request
1. Did the payer's InsurancePlan for claim NM-26-0VL00003S arrive (check docker logs)?
2. Can we handle a 60–100 MB plan (Django body limits, envs, middleware)?
3. Is the plan fetched per claim, per patient or per facility?

Running stack: `care-nhcx-backend` mounts `khavinshankar-silver-sniffle/care`
(HEAD a5426abad) under `runserver_plus`, reached via a cloudflared tunnel.

## 1. It arrived, and we refused it
- 14:56:24 IST `v1/insuranceplan/request` sent to 1518@hcx, 202 (ledger 7USL00S6,
  correlation 84c8cc15-887d-4875-b1a7-ba04c9731db5).
- `/in/v1/insuranceplan/on_request` was POSTed three times (14:56:31, 14:56:35,
  14:57:35). All were answered **400 INVALID_BODY** ("body must be a JSON object").
  The ledger entries 7USL00S7/S8/S9 have empty headers, so even header peeking
  failed: the bytes we read were empty or not JSON.
- `nhcx_claimplan` for the claim is still `status=fetching`, with `fetched_at` null.
- The earlier plan (7USL00G2, 228 KB, 12:05) went through the same tunnel fine.
- Reproduced locally against :9000: `Transfer-Encoding: chunked` and
  `Content-Encoding: gzip` bodies both give exactly this INVALID_BODY; plain JSON
  is accepted. Likely cause: a large body comes through cloudflared/payer as
  chunked (Django builds `LimitedStream` from `CONTENT_LENGTH`, which is 0, so
  `request.read()` returns `b""`) or gzip-compressed (we never decode it). We
  can't tell which, because the refusal doesn't log the body length or the
  Content-Length/Transfer-Encoding/Content-Encoding headers.
- Side effect: the probes added three ledger entries (two rejected, one `{"a":1}`
  json delivery).

## 2. Readiness for 60–100 MB plans: partially ready
- `DATA_UPLOAD_MAX_MEMORY_SIZE` doesn't apply. `care/nhcx/gateway/views.py` uses
  `request.read(limit+1)`, not `request.body`, and no middleware touches the body.
  No env change is needed for Django itself.
- The gateway cap is `maxBodyBytes`. It isn't set in `~/.nhcx/sandbox/gateway.json`,
  so it defaults to 100 MiB. A JWE is about 1.33x the plaintext (base64url), so a
  plan over about 75 MB would get 413 BODY_TOO_LARGE. Raise the cap to about
  200 MB.
- Gaps: chunked bodies aren't supported, `Content-Encoding: gzip` isn't decoded,
  and Cloudflare's edge body cap (100 MB on Free/Pro) applies before ours.
- Memory: the raw body, JWE decode, plaintext and parsed dict are all held in one
  synchronous request (several hundred MB peak). After that the full bundle is
  written to the ledger file, the archive and `nhcx_claimplan.response_json`.

## 3. Fetch scope
`services/plan.py`: `ClaimPlan` is one-to-one with a **claim**. `request_plan`
first calls `reuse_plan`, which copies the newest `ready` plan with the same
**policy_code + facility HFR ID + payer_id** (no expiry). In effect we fetch once
per (payer, policy/product, facility) and copy it to each claim. This claim
(PMJAY/HP/S/G, IN2910001986, 1518@hcx) had no ready match, so we fetched. The copy
duplicates `response_json` per claim, which means about 100 MB per claim at
full size.

## Open items (not done; await user decision)
- Log the body length and the CL/TE/CE headers on refusal.
- Read chunked bodies until EOF (`wsgi.input_terminated`) and gunzip when
  `Content-Encoding: gzip`.
- Raise `maxBodyBytes`, check Cloudflare plan limits, and stream or offload large
  bodies.
- Store the plan once per (payer, policy, HFR) instead of copying `response_json`
  per claim. Add a reuse TTL or refresh.
- Re-request the plan for NM-26-0VL00003S once the fix lands.
