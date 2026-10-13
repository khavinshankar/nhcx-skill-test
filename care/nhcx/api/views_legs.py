"""Facility-scoped NHCX leg routes (api/CONTRACT.md "legs"), mounted by api/urls.py
under /api/v1/facility/<facility_external_id>/nhcx/.

Sending routes run outside ATOMIC_REQUESTS (``SendingView``): a gateway call
must not sit inside a transaction, and a failed send keeps its row and ids.
"""

from __future__ import annotations

from django.http import Http404

from care.nhcx.api.views_core import (
    NhcxFacilityView,
    SendingView,
    ok,
    refusals,
    refused,
)
from care.nhcx.models import ClaimPayment, ClaimQuery, FacilityProfile
from care.nhcx.services import (
    adjudicator,
    biometric,
    communication,
    draft,
    payment,
    preauth,
)
from care.nhcx.services import claim as claim_service
from care.nhcx.services.common import ServiceRefusal

EXCHANGE_FAILED = "The exchange failed."
PREAUTH_SUBMITTED = "Pre-authorisation submitted to the payer."
PREDETERMINATION_SENT = "Predetermination sent to the payer."
CANCEL_SENT = "Cancellation sent to the payer."
STATUS_SENT = "Status enquiry sent to the payer."
REPROCESS_SENT = "Reprocess request sent to the payer."
RELEASE_SENT = "Balance release request sent to the payer."
CLAIM_SUBMITTED = "Claim submitted to the payer."
REPLY_SENT = "Reply sent to the payer."
ACK_SENT = "Acknowledgement sent to the payer."
PAYMENT_ACKED = "Payment acknowledged to the payer."
ATTACHED = "{n} document(s) attached."
SETTINGS_SAVED = "Facility settings saved."
NO_FILE = "Choose a PDF or image to attach."
ENQUIRY_SENT = {
    "status": STATUS_SENT,
    "reprocess": REPROCESS_SENT,
    "release": RELEASE_SENT,
}
PROFILE_FIELDS = ("hfr_id", "participant_code", "email", "gstin")


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def _body(request) -> dict:
    data = request.data
    if hasattr(data, "dict"):
        return data.dict()
    return dict(data or {})


def _sent(row, message, claim, **extra):
    """200 with the message, or 400 naming the failure when the send failed; the
    row (and the ids it already holds) is kept either way."""
    if _s(getattr(row, "status", "")) == "error":
        error = _s(getattr(row, "error_message", "")) or EXCHANGE_FAILED
        return refused(error) if claim is None else _failed(error, claim)
    return ok(message, claim, **extra)


def _failed(error, claim):
    response = refused(error)
    response.data["claim_id"] = str(claim.external_id)
    return response


def _upload(request):
    f = request.FILES.get("file")
    if f is None:
        return None
    return {
        "filename": f.name,
        "content_type": _s(f.content_type),
        "data": f.read(),
    }


class DraftView(NhcxFacilityView):
    @refusals
    def put(self, request, facility_external_id, claim_id):
        case = self.claim(claim_id)
        return ok(draft.save_draft(case, _body(request)), case)


class DocumentsView(NhcxFacilityView):
    @refusals
    def post(self, request, facility_external_id, claim_id):
        case = self.claim(claim_id)
        upload = _upload(request)
        if upload is None:
            raise ServiceRefusal(NO_FILE)
        data = request.data
        doc = draft.attach(
            case,
            upload,
            code=_s(data.get("code")),
            category=_s(data.get("category")),
            leg=_s(data.get("stage")) or "preauth",
            label=_s(data.get("label")),
        )
        return ok(ATTACHED.format(n=1), case, document_id=str(doc.external_id))


class DocumentDetailView(NhcxFacilityView):
    @refusals
    def delete(self, request, facility_external_id, claim_id, doc_id):
        case = self.claim(claim_id)
        return ok(draft.remove_document(case, doc_id), case)


class PreauthSubmitView(SendingView):
    @refusals
    def post(self, request, facility_external_id, claim_id):
        case = self.claim(claim_id)
        data = _body(request)
        row = preauth.submit_preauth(case, _s(data.get("reply")))
        return _sent(row, PREAUTH_SUBMITTED, case)


class PredeterminationView(SendingView):
    @refusals
    def post(self, request, facility_external_id, claim_id):
        case = self.claim(claim_id)
        row = preauth.ask_predetermination(case)
        return _sent(row, PREDETERMINATION_SENT, case)


class PreauthCancelView(SendingView):
    @refusals
    def post(self, request, facility_external_id, claim_id):
        case = self.claim(claim_id)
        data = _body(request)
        row = preauth.cancel_preauth(case, _s(data.get("reason")), _s(data.get("note")))
        if _s(row.status) == "error":
            return _failed(_s(row.error_message) or EXCHANGE_FAILED, case)
        return ok(CANCEL_SENT, case)


class EnquiryView(SendingView):
    @refusals
    def post(self, request, facility_external_id, claim_id):
        case = self.claim(claim_id)
        data = _body(request)
        action = _s(data.get("action")) or "status"
        row = claim_service.enquire(
            case,
            action,
            leg=_s(data.get("leg")),
            reason=_s(data.get("reason")),
            note=_s(data.get("note")),
            amount=data.get("amount"),
            reason_code=_s(data.get("reason_code")),
            document_ids=data.get("document_ids") or None,
        )
        return _sent(
            row,
            ENQUIRY_SENT.get(action, STATUS_SENT),
            case,
            enquiry_id=str(row.external_id),
        )


class ClaimSubmitView(SendingView):
    @refusals
    def post(self, request, facility_external_id, claim_id):
        case = self.claim(claim_id)
        data = _body(request)
        if _s(data.get("discharge_mode")):
            claim_service.record_discharge(case, data)
            case = self.claim(claim_id)
        row = claim_service.submit_claim(case, _s(data.get("reply")))
        return _sent(row, CLAIM_SUBMITTED, case)


class DischargeView(NhcxFacilityView):
    @refusals
    def post(self, request, facility_external_id, claim_id):
        case = self.claim(claim_id)
        claim_service.record_discharge(case, _body(request))
        return ok(claim_service.DISCHARGE_RECORDED, case)


class QueryReplyView(SendingView):
    @refusals
    def post(self, request, facility_external_id, claim_id, query_id):
        case = self.claim(claim_id)
        asked = ClaimQuery.objects.filter(claim=case, external_id=query_id).first()
        if asked is None:
            raise Http404
        data = request.data
        ids = data.getlist("document_ids") if hasattr(data, "getlist") else None
        ids = ids or data.get("document_ids") or []
        uploads = []
        for f in request.FILES.getlist("files") if request.FILES else []:
            uploads.append(
                {
                    "filename": f.name,
                    "content_type": _s(f.content_type),
                    "data": f.read(),
                }
            )
        communication.answer_query(
            asked.id,
            _s(data.get("text")),
            _document_pks(case, ids),
            uploads,
            claim=case,
        )
        return ok(REPLY_SENT, case)


class QueryAckView(SendingView):
    @refusals
    def post(self, request, facility_external_id, claim_id, query_id):
        case = self.claim(claim_id)
        asked = ClaimQuery.objects.filter(claim=case, external_id=query_id).first()
        if asked is None:
            raise Http404
        communication.acknowledge_notification(asked.id, claim=case)
        return ok(ACK_SENT, case)


def _document_pks(case, ids):
    from care.nhcx.models import ClaimDocument

    out = []
    for given in ids or []:
        ref = _s(given)
        if not ref:
            continue
        if ref.isdigit():
            out.append(int(ref))
            continue
        doc = ClaimDocument.objects.filter(claim=case, external_id=ref).first()
        if doc is None:
            raise ServiceRefusal(communication.f12.DOCUMENT_NOT_ON_CLAIM)
        out.append(doc.id)
    return out


class PaymentAckView(SendingView):
    @refusals
    def post(self, request, facility_external_id, claim_id, payment_id):
        case = self.claim(claim_id)
        money = ClaimPayment.objects.filter(claim=case, external_id=payment_id).first()
        if money is None:
            raise Http404
        payment.acknowledge_payment(money.id, claim=case)
        return ok(PAYMENT_ACKED, case)


class BiometricView(SendingView):
    def get(self, request, facility_external_id, claim_id):
        case = self.claim(claim_id)
        return ok(None, case, **biometric.listing(case))

    @refusals
    def post(self, request, facility_external_id, claim_id, action):
        case = self.claim(claim_id)
        data = _body(request)
        if action == "init":
            row, qr = biometric.init(
                case,
                _s(data.get("method")) or "FACE_AUTH",
                stage=_s(data.get("stage")) or None,
                abha_no=_s(data.get("abha_no")) or None,
                user=request.user,
                payer_code=_s(data.get("payer_code")) or None,
            )
            return ok(None, case, attempt=biometric.describe(row), qr_url=qr)
        row = biometric.attempt(case, data.get("attempt_id"))
        if action == "capture":
            row, state = biometric.capture(row)
            return ok(None, case, attempt=biometric.describe(row), capture=state)
        if action == "verify":
            row = biometric.verify(
                row,
                pid=_s(data.get("pid")),
                aadhaar_encrypted=_s(data.get("aadhaar_encrypted")),
                mobile=_s(data.get("mobile")),
            )
            return ok(_s(row.message) or None, case, attempt=biometric.describe(row))
        if action == "refresh":
            row = biometric.refresh(row)
            return ok(None, case, attempt=biometric.describe(row))
        raise Http404


class AdjudicateView(SendingView):
    def initial(self, request, *args, **kwargs):
        if not adjudicator.enabled():
            raise Http404
        super().initial(request, *args, **kwargs)

    @refusals
    def post(self, request, facility_external_id, claim_id):
        case = self.claim(claim_id)
        result = adjudicator.adjudicate(case, _body(request))
        message = result.pop("message", None)
        if result.get("success") is False:
            response = refused(message or EXCHANGE_FAILED)
            response.data.update(result)
            response.data["claim_id"] = str(case.external_id)
            return response
        return ok(message, case, **result)


class FacilityProfileView(NhcxFacilityView):
    def _profile(self):
        return FacilityProfile.objects.filter(facility=self.facility).first()

    def get(self, request, facility_external_id):
        found = self._profile()
        return ok(
            None,
            profile={k: _s(getattr(found, k, "")) for k in PROFILE_FIELDS},
        )

    def put(self, request, facility_external_id):
        data = _body(request)
        found = self._profile() or FacilityProfile(facility=self.facility)
        for k in PROFILE_FIELDS:
            if k in data:
                setattr(found, k, _s(data.get(k)) or None)
        found.save()
        return ok(
            SETTINGS_SAVED,
            profile={k: _s(getattr(found, k, "")) for k in PROFILE_FIELDS},
        )


__all__ = [
    "AdjudicateView",
    "BiometricView",
    "ClaimSubmitView",
    "DischargeView",
    "DocumentDetailView",
    "DocumentsView",
    "DraftView",
    "EnquiryView",
    "FacilityProfileView",
    "PaymentAckView",
    "PreauthCancelView",
    "PreauthSubmitView",
    "PredeterminationView",
    "QueryAckView",
    "QueryReplyView",
]
