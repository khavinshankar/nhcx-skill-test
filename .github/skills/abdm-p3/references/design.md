# Design P3, PHR subscriptions

What the integration has to do to the journey around the calls: how many questions a patient is asked, where a failure is shown, and what a screen is forbidden to claim. Every rule below comes from a Catalogue atom, cited at the end.

## The five things a personal health record application must let a person do with consent

### In plain words

Consent is granted by a person, and the PHR app is where they do it. There is
a floor of five capabilities, and an app missing one leaves a person able to
give access they cannot inspect, change or withdraw.

1. **See the request**, with the HIU asking, the purpose, the record types,
   the date range of records, how long the consent would last, and its status.
2. **Change it before allowing it**, where the request permits: the access
   duration, the record date range, the categories shared, and the validity
   period. This is the one most often left out, and the one that turns a
   consent screen into a negotiation rather than a demand.
3. **Allow or refuse it.** The consent flow has three outcomes, not two:
   approve, reject and ignore. An ignored request expires on the requester's
   window, and the interface has to show that state.
4. **See what is already allowed**, so the person can tell which
   organisations hold access right now. A list of past decisions is not the
   same thing.
5. **Take it back** at any time. Two things follow: the status updates at the
   consent manager, and sharing under that consent stops immediately, not at
   the end of the period.

### What happens

Build a screen for each of the five. Approving posts to `/api/hiecm/consent/v3/request/{consentRequestId}/approve`, denying to `/api/hiecm/consent/v3/request/{consentRequestId}/deny`, and revoking a granted consent to `/api/hiecm/consent/v3/revoke`. Show Expired as its own state, never as Denied, because the person refused nothing.

### How you know it worked

One request goes through the whole arc in the app: seen, its date range narrowed, allowed, found in the list of live consents, and revoked. A fetch attempted under it afterwards fails.

### When it goes wrong

A screen that lists requests but not live consents leaves the person unable to revoke what they cannot see. Revocation shown as expiry hides a decision the person made. Leaving out modification turns consent into a notice.

## Subscriptions, and why a personal health record application needs one

### In plain words

Ask the user for consent before you create a subscription. An approved
subscription notifies your app when a care context is linked or updated. Surface these as device
notifications.

You need screens to list subscriptions, approve them, deny them and edit them.
Editing covers health information types, purpose, categories and the time period.

A subscription tells you a record exists. It is not consent, and it gives nobody
the record: reading it still needs a consent request, which is why a
subscription usually runs beside an auto approval policy.

### What happens

Raise the subscription with `/api/hiecm/subscription-requests/v3/init`; the request id arrives on `/api/v3/hiu/hiecm/subscription-requests/on-init`. The person approves it with `/api/hiecm/subscription-requests/v3/{subscriptionRequestId}/approve` or denies it. Once approved, notifications arrive on `/api/v3/hiu/subscription/notify`, in the categories `LINK` and `DATA`, and you acknowledge each with `/api/hiecm/subscription-requests/v3/hiu/care-context/on-notify`. Set one up when you create an address and when a person signs in with an address the install has not seen.

### How you know it worked

The subscription shows as approved, and linking a care context to that address from a facility produces a notification on your callback without any call from you.

### When it goes wrong

Nothing arrives: the checks are those for any callback, see [the callback never arrives](/docs/hiecm/v3/troubleshooting/callback-never-arrives). A subscription created without asking the person is a consent failure that certification looks for. A notification acted on as though it were permission reads a record with no consent behind it.

## Where these came from

- `hiecm.concept.consent-in-a-phr-app`
- `hiecm.concept.phr-subscriptions`
