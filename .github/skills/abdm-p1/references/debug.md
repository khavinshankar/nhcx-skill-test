# HIE-CM p1 debug

Every error below is an OODA loop: observe the error code and last request id, orient against the matched code, decide the fix, act, and observe whether the original step now succeeds. Applying a fix is not the exit condition; the original step succeeding is.

Loop limit: 5 passes per error.

## Errors

### 900902

**Specification example:** HTTP 401, `Missing Credentials`, on `p1_get_v3_phr_app_enrollment_isexists`.

**Exit condition: the original call now succeeds.**

### ABDM-1107

**Specification example:** HTTP 400, `Invalid combinations of scopes`, on `p1_post_v3_phr_app_login_verify`.

**Exit condition: the original call now succeeds.**

### ABDM-1211

**Specification example:** HTTP 400, `User not found.`, on `p1_post_v3_phr_app_login_search`.

**Exit condition: the original call now succeeds.**

### ABDM-9999

**Specification example:** HTTP 400, `Invalid LoginId`, on `p1_post_v3_phr_app_enrollment_request_otp`.

**Exit condition: the original call now succeeds.**

## Where the detail is

- The operation that returns each code: /docs/hiecm/v3/api/p1

## Every code in the specification

### Codes

| Code | HTTP | Message | Returned by |
| --- | --- | --- | --- |
| `900902` | 401 | Missing Credentials | `p1_get_v3_phr_app_enrollment_isexists` |
| `ABDM-1107` | 400 | Invalid combinations of scopes | `p1_post_v3_phr_app_login_verify` |
| `ABDM-1211` | 400 | User not found. | `p1_post_v3_phr_app_login_search` |
| `ABDM-9999` | 400 | Invalid LoginId | `p1_post_v3_phr_app_enrollment_request_otp` |

A code you meet that is not above is one the specifications do not carry yet. Read the code together with the message: a code can appear twice with different meanings.
