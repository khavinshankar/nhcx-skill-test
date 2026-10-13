# Integrate P1, PHR registration and login

The calls themselves: where they live, what they need in their headers, and one request written out in full.

## Hosts

- `https://abhasbx.abdm.gov.in` ABHA service, sandbox
- `https://dev.abdm.gov.in` ABDM gateway, sandbox
- `https://apis.abdm.gov.in` ABDM gateway, production
## Endpoints

15 operations, grouped by the journey they belong to.

### Other operations

| Method | Path | What it does |
| --- | --- | --- |
| `POST` | `/abha/api/v3/phr/app/enrollment/enrol` | 3 flows: Enrol ABHA Address |
| `GET` | `/abha/api/v3/phr/app/enrollment/isExists` | 3 flows: isExists API, isExists API Copy |
| `POST` | `/abha/api/v3/phr/app/enrollment/request/otp` | 3 flows: OTP Request - Mobile, OTP Request - ABHA OTP, OTP Request - AADHAR OTP |
| `POST` | `/abha/api/v3/phr/app/enrollment/suggestion` | 3 flows: Suggestion API |
| `POST` | `/abha/api/v3/phr/app/enrollment/verify` | 3 flows: OTP Verify - Mobile, OTP Verify - ABHA OTP, OTP Verify - AADHAR OTP |
| `GET` | `/abha/api/v3/phr/app/login/public/certificate` | PHR Certificate |
| `POST` | `/abha/api/v3/phr/app/login/request/otp` | 5 flows: OTP Request - Mobile, OTP Request - ABHAADDRES Mobile, OTP Request - A… |
| `POST` | `/abha/api/v3/phr/app/login/search` | Search Auth Methods - ABHAAddress |
| `POST` | `/abha/api/v3/phr/app/login/verify` | 6 flows: Login OTP Verify - Mobile, Login OTP Verify - ABHAADDRES Mobile, Login… |
| `POST` | `/abha/api/v3/phr/app/login/verify/user` | 5 flows: Verify User, Verify - User |
| `POST` | `/abha/api/v3/profile/account/request/emailVerificationLink` | Email Verification Link |
| `GET` | `/api/hiecm/gateway/v3/bridge-service/serviceId/{service-id}` | Fetch the details of a service ID. |
| `GET` | `/api/hiecm/gateway/v3/bridge-services` | Fetch the service ids registered against a bridge. |
| `PATCH` | `/api/hiecm/gateway/v3/bridge/url` | Update the bridge URL. |
| `POST` | `/api/hiecm/gateway/v3/sessions` | Generate access token. |
## Headers

| Header | What it is |
| --- | --- |
| `REQUEST-ID` | Unique UUID for each request. |
| `TIMESTAMP` | Request timestamp in UTC, ISO-8601 with Z. |
| `T-token` | The transaction token from the preceding login step, sent with a `Bearer ` prefix. It is valid only for that … |
| `X-token` | The user token from a login or enrolment response, sent with a `Bearer ` prefix. It acts for that ABHA holder. |
| `X-CM-ID` | Suffix of the consent manager to which the request was intended |
## A request, in full

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/enrol \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "txnId": "27d444b7-2a3d-46d8-bf67-e5590b6c46b6",
  "phrDetails": {
    "mobile": "<ENCRYPTED_MOBILE>",
    "firstName": "John",
    "middleName": "",
    "lastName": "Doe",
    "yearOfBirth": "<DOB>",
    "dayOfBirth": "",
    "monthOfBirth": "<DOB>",
    "gender": "M",
    "email": "",
    "profilePhoto": "",
    "address": "<ADDRESS>",
    "stateName": "Maharashtra",
    "stateCode": "27",
    "districtName": "<ADDRESS>",
    "districtCode": "123",
    "pinCode": "<PINCODE>",
    "abhaAddress": "<ABHA_ADDRESS>",
    "password": "<ENCRYPTED_PASSWORD>"
  }
}'
```
