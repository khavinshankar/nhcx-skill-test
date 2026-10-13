"""Leg routes (api/CONTRACT.md "legs"), included by api/urls.py under the facility prefix."""

from django.urls import path

from care.nhcx.api import views_legs as v

C = "claims/<uuid:claim_id>/"

urlpatterns = [
    path(C + "draft/", v.DraftView.as_view(), name="nhcx-claim-draft"),
    path(C + "documents/", v.DocumentsView.as_view(), name="nhcx-claim-documents"),
    path(
        C + "documents/<uuid:doc_id>/",
        v.DocumentDetailView.as_view(),
        name="nhcx-claim-document",
    ),
    path(
        C + "preauth/submit/",
        v.PreauthSubmitView.as_view(),
        name="nhcx-preauth-submit",
    ),
    path(
        C + "preauth/predetermination/",
        v.PredeterminationView.as_view(),
        name="nhcx-preauth-predetermination",
    ),
    path(
        C + "preauth/cancel/", v.PreauthCancelView.as_view(), name="nhcx-preauth-cancel"
    ),
    path(C + "enquiry/", v.EnquiryView.as_view(), name="nhcx-claim-enquiry"),
    path(C + "discharge/", v.DischargeView.as_view(), name="nhcx-claim-discharge"),
    path(C + "claim/submit/", v.ClaimSubmitView.as_view(), name="nhcx-claim-submit"),
    path(
        C + "queries/<uuid:query_id>/reply/",
        v.QueryReplyView.as_view(),
        name="nhcx-query-reply",
    ),
    path(
        C + "queries/<uuid:query_id>/ack/",
        v.QueryAckView.as_view(),
        name="nhcx-query-ack",
    ),
    path(
        C + "payments/<uuid:payment_id>/ack/",
        v.PaymentAckView.as_view(),
        name="nhcx-payment-ack",
    ),
    path(C + "biometric/", v.BiometricView.as_view(), name="nhcx-biometric"),
    path(
        C + "biometric/<str:action>/",
        v.BiometricView.as_view(),
        name="nhcx-biometric-action",
    ),
    path(C + "adjudicate/", v.AdjudicateView.as_view(), name="nhcx-adjudicate"),
    path("profile/", v.FacilityProfileView.as_view(), name="nhcx-facility-profile"),
]
