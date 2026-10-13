# Integrate Scan and pay

The calls themselves: where they live, what they need in their headers, and one request written out in full.

## Hosts

- `https://dev.abdm.gov.in` ABDM gateway, sandbox
- `https://apis.abdm.gov.in` ABDM gateway, production
## Endpoints

22 operations, grouped by the journey they belong to.

### Other operations

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/api/hiecm/gateway/v3/bridge-service/serviceId/{service-id}` | Fetch the details of a service ID. |
| `GET` | `/api/hiecm/gateway/v3/bridge-services` | Fetch the service ids registered against a bridge. |
| `PATCH` | `/api/hiecm/gateway/v3/bridge/url` | Update the bridge URL. |
| `PATCH` | `/api/hiecm/gateway/v3/scanPay/updateVersion` | Update version to the serviceId. |
| `POST` | `/api/hiecm/gateway/v3/sessions` | Generate access token. |
| `POST` | `/api/hiecm/scan-gateway/v3/patient/on-selection` | Share payment bundle alone with procedures of the patient. |
| `POST` | `/api/hiecm/scan-gateway/v3/patient/on-share/open-order` | HIE-CM to send all the open order for patient. |
| `GET` | `/api/hiecm/scan-gateway/v3/patient/scan-pay/details` | This is retrieve the all the details of the user. |
| `POST` | `/api/hiecm/scan-gateway/v3/patient/scan-pay/notify` | Send the payment status to HIU. |
| `POST` | `/api/hiecm/scan-gateway/v3/patient/scan-pay/on-notify` | Notify to HIP so that confirm that the HIU received the payment status. |
| `POST` | `/api/hiecm/scan-gateway/v3/patient/scan-pay/on-order-status` | Check the status of reports. |
| `POST` | `/api/hiecm/scan-gateway/v3/patient/scan-pay/order-status` | Check the status of reports. |
| `POST` | `/api/hiecm/scan-gateway/v3/patient/selection` | Select the all open-order and send to HIP for a payment request detail. |
| `POST` | `/api/hiecm/scan-gateway/v3/patient/share/open-order` | Be invoked from the integrator application (any PHR application, just like ABHA… |
| `POST` | `/v3/patient/on-selection` | This is callback API for the API. This API needs to implement by HIU to receive… |
| `POST` | `/v3/patient/on-share/open-order` | This is a callback API for patient on-share. This API needs to implement by HIU… |
| `POST` | `/v3/patient/scan-pay/notify` | This is callback API for the notify API. This API needs to implement by HIU to … |
| `POST` | `/v3/patient/scan-pay/on-notify` | This is an callback API for on-notify API need to implement by HIP to received … |
| `POST` | `/v3/patient/scan-pay/on-order-status` | This is callback for the on-order-status API. This API needs to implement by HI… |
| `POST` | `/v3/patient/scan-pay/order-status` | This is callback API for the order_status API. This API needs to implement by H… |
| `POST` | `/v3/patient/selection` | This is the call back API for the selection API. This API needs to implement by… |
| `POST` | `/v3/patient/share/open-order` | Check the status of reports. |
## Headers

| Header | What it is |
| --- | --- |
| `REQUEST-ID` | Unique UUID for track the end to end request transaction |
| `TIMESTAMP` | Actual time of the request was initiated, ISO 8601 represents date and time by starting with the year, follow… |
| `X-CM-ID` | Suffix of the consent manager to which the request was intended |
| `X-AUTH-TOKEN` | JWT Authentication token which was issued by ABDM after successful validation of username and password |
| `X-HIP-ID` | Identifier of the health information provider to which the request was intended |
| `X-HIU-ID` | Identifier of the health information user to which the request was intended |
## A request, in full

```bash
curl --request GET \
  --url https://dev.abdm.gov.in/api/hiecm/gateway/v3/bridge-service/serviceId/{service-id} \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx'
```
