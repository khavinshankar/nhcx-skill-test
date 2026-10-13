"""Facility-scoped NHCX routes, mounted at /api/v1/facility/<facility_external_id>/nhcx/."""

import importlib

from django.urls import include, path

from care.nhcx.api import views_core as v

urlpatterns = [
    path("policy-search/", v.PolicySearchView.as_view(), name="nhcx-policy-search"),
    path("claims/", v.ClaimListView.as_view(), name="nhcx-claims"),
    path(
        "claims/<uuid:claim_id>/state/",
        v.ClaimStateView.as_view(),
        name="nhcx-claim-state",
    ),
    path(
        "claims/<uuid:claim_id>/eligibility/",
        v.EligibilityView.as_view(),
        name="nhcx-claim-eligibility",
    ),
    path(
        "claims/<uuid:claim_id>/auth-requirements/",
        v.AuthRequirementsView.as_view(),
        name="nhcx-claim-auth-requirements",
    ),
    path("claims/<uuid:claim_id>/plan/", v.PlanView.as_view(), name="nhcx-claim-plan"),
    path(
        "claims/<uuid:claim_id>/plan/benefits/<uuid:benefit_id>/",
        v.PlanBenefitView.as_view(),
        name="nhcx-claim-plan-benefit",
    ),
    path(
        "claims/<uuid:claim_id>/lines/", v.LinesView.as_view(), name="nhcx-claim-lines"
    ),
    path(
        "claims/<uuid:claim_id>/lines/<uuid:line_id>/",
        v.LineDetailView.as_view(),
        name="nhcx-claim-line",
    ),
    path(
        "claims/<uuid:claim_id>/admission/",
        v.AdmissionView.as_view(),
        name="nhcx-claim-admission",
    ),
    path("ledger/", v.LedgerView.as_view(), name="nhcx-ledger"),
    path("ledger/<str:entry_id>/", v.LedgerView.as_view(), name="nhcx-ledger-entry"),
]

try:
    urls_legs = importlib.import_module("care.nhcx.api.urls_legs")
except ImportError as e:
    if e.name != "care.nhcx.api.urls_legs":
        raise
    urls_legs = None

if urls_legs is not None:
    urlpatterns.append(path("", include(urls_legs)))
