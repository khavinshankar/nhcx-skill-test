# HIE-CM p2 debug

Every error below is an OODA loop: observe the error code and last request id, orient against the matched code, decide the fix, act, and observe whether the original step now succeeds. Applying a fix is not the exit condition; the original step succeeding is.

Loop limit: 5 passes per error.

## Errors

### 900902

**Specification example:** HTTP 401, `Missing Credentials`, on `p2_get_v3_phr_app_login_profile`.

**Exit condition: the original call now succeeds.**

### ABDM-9999

**Specification example:** HTTP 400, `Invalid LoginId`, on `p2_post_v3_phr_app_login_profile_request_otp`.

**Exit condition: the original call now succeeds.**

## Where the detail is

- The operation that returns each code: /docs/hiecm/v3/api/p2

## Every code in the specification

### Codes

| Code | HTTP | Message | Returned by |
| --- | --- | --- | --- |
| `900902` | 401 | Missing Credentials | `p2_get_v3_phr_app_login_profile` |
| `ABDM-9999` | 400 | Invalid LoginId | `p2_post_v3_phr_app_login_profile_request_otp` |

A code you meet that is not above is one the specifications do not carry yet. Read the code together with the message: a code can appear twice with different meanings.
