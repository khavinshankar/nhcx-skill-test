# Integrate Patient scan and record share

The calls themselves: where they live, what they need in their headers, and one request written out in full.

## Hosts

- `https://dev.abdm.gov.in` ABDM gateway, sandbox. X-CM-ID is sbx.
- `https://apis.abdm.gov.in` ABDM gateway, production. X-CM-ID is abdm.
## Endpoints

12 operations, grouped by the journey they belong to.

### Other operations

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/api/hiecm/gateway/v3/bridge-service/serviceId/{service-id}` | Fetch the details of a service ID. |
| `GET` | `/api/hiecm/gateway/v3/bridge-services` | Fetch the service ids registered against a bridge. |
| `PATCH` | `/api/hiecm/gateway/v3/bridge/url` | Update the bridge URL. |
| `POST` | `/api/hiecm/gateway/v3/sessions` | Generate access token. |
| `GET` | `/api/hiecm/patient-record/v3/audit-history` | List the record sharing history of the signed in user. |
| `POST` | `/api/hiecm/patient-record/v3/notify` | Notify the HIE-CM of the transfer status, once, after the data transfer complet… |
| `POST` | `/api/hiecm/patient-record/v3/on-share` | Reply to a share request with the data push URL and the encryption key. |
| `POST` | `/api/hiecm/patient-record/v3/share` | Share a patient's records with the HIU whose QR code was scanned. |
| `POST` | `/api/v3/patient-record/on-notify` | Receive the other side's transfer status. |
| `POST` | `/api/v3/patient-record/on-share` | Receive the HIU's data push URL and encryption key, as the PHR app. |
| `POST` | `/api/v3/patient-record/share` | Receive a patient's share request, as the HIU. |
| `POST` | `/health-information/transfer` | Receive the encrypted records at the data push URL, as the HIU. |
## Headers

| Header | What it is |
| --- | --- |
| `REQUEST-ID` | Unique UUID for track the end to end request transaction |
| `TIMESTAMP` | Actual time of the request was initiated, ISO 8601 represents date and time by starting with the year, follow… |
| `X-CM-ID` | Suffix of the consent manager to which the request was intended |
| `X-AUTH-TOKEN` | JWT access token issued by the PHR service after successful user authentication. If the HIP does not have any… |
| `X-HIU-ID` | Identifier of the health information user to which the request was intended. |
| `request-id` | Random UUID, a v4 style guid, unique per callback. |
| `timestamp` | ISO 8601 timestamp of when the callback was sent. |
| `x-hiu-id` | Identifier of the health information user to which the request was intended. |
## A request, in full

```bash
curl --request GET \
  --url https://dev.abdm.gov.in/api/hiecm/gateway/v3/bridge-service/serviceId/{service-id} \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx'
```
