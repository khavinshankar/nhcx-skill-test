"""Facility-scoped NHCX API owned by services-core (api/CONTRACT.md "core").

Shared with views_legs (keep names stable):
- ``NhcxFacilityView``: APIView that authenticates (401), resolves the URL's
  ``facility_external_id`` into ``self.facility`` and checks the user can see
  that facility (403); ``self.claim(claim_id)`` answers the facility's claim
  or raises Http404.
- ``SendingView``: ``NhcxFacilityView`` outside ATOMIC_REQUESTS, for routes
  that call the gateway.
- ``ok(message=None, claim=None, **extra)`` / ``refused(message, status=400)``.
- ``refusals``: decorator turning ``ServiceRefusal`` into ``refused(...)``.
"""

import functools
import uuid

from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import status as http
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.facility.models import Facility
from care.nhcx.gateway import get_gateway
from care.nhcx.gateway.errors import GatewayError
from care.nhcx.models import Claim
from care.nhcx.services import eligibility, lines, plan, policy
from care.nhcx.services.common import ServiceRefusal
from care.nhcx.services.state import claim_state, row

NO_ACCESS = "You do not have access to this facility."
NO_SUCH_CLAIM = "No such claim"
ELIGIBILITY_QUEUED = "Eligibility request queued to the payer."
PLAN_REQUESTED = "Insurance plan requested from the payer."
PLAN_REUSED = (
    "Using the package master already held for this policy - Fetch again asks "
    "the payer for a new one."
)
AUTH_SENT = "Procedure set sent to the payer for validation."
CLAIM_LIST_LIMIT = 100


def ok(message=None, claim=None, **extra) -> Response:
    body = {"ok": True, "message": message}
    if claim is not None:
        body["claim_id"] = str(claim.external_id)
    body.update(extra)
    return Response(body)


def refused(message, status=http.HTTP_400_BAD_REQUEST) -> Response:
    return Response({"ok": False, "error": str(message)}, status=status)


def refusals(fn):
    @functools.wraps(fn)
    def wrapper(self, request, *args, **kwargs):
        try:
            return fn(self, request, *args, **kwargs)
        except ServiceRefusal as e:
            return refused(e.message)

    return wrapper


def can_access_facility(user, facility) -> bool:
    if user.is_superuser:
        return True
    if FacilityOrganizationUser.objects.filter(
        user=user, organization__facility=facility
    ).exists():
        return True
    org_ids = list(
        OrganizationUser.objects.filter(user=user).values_list(
            "organization_id", flat=True
        )
    )
    return (
        bool(org_ids)
        and Facility.objects.filter(
            Q(id=facility.id) & Q(geo_organization_cache__overlap=org_ids)
        ).exists()
    )


class NhcxFacilityView(APIView):
    facility = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.facility = get_object_or_404(
            Facility, external_id=kwargs.get("facility_external_id")
        )
        if not can_access_facility(request.user, self.facility):
            raise PermissionDenied(NO_ACCESS)

    def claim(self, claim_id) -> Claim:
        found = (
            Claim.objects.filter(facility=self.facility, external_id=claim_id)
            .select_related("facility", "patient", "encounter")
            .first()
        )
        if found is None:
            raise Http404(NO_SUCH_CLAIM)
        return found


@method_decorator(transaction.non_atomic_requests, name="dispatch")
class SendingView(NhcxFacilityView):
    pass


def _external_id(value, label):
    try:
        return uuid.UUID(str(value))
    except ValueError:
        message = f"{label} id {value!r} is not a valid UUID."
        raise ServiceRefusal(message) from None


def _patient(facility, patient_id):
    if not patient_id:
        return None
    from care.emr.models import Patient

    return Patient.objects.filter(
        external_id=_external_id(patient_id, "Patient")
    ).first()


def _encounter(facility, encounter_id):
    if not encounter_id:
        return None
    from care.emr.models import Encounter

    return (
        Encounter.objects.filter(
            external_id=_external_id(encounter_id, "Encounter"), facility=facility
        )
        .select_related("patient")
        .first()
    )


SEARCH_KEYS = (
    ("abha_number", "AbhaNumber"),
    ("mobile", "MobileNo"),
    ("mobile_number", "MobileNo"),
    ("member_id", "MemberId"),
)


class PolicySearchView(SendingView):
    @refusals
    def post(self, request, facility_external_id):
        data = request.data or {}
        id_type, id_value = data.get("identifiertype"), data.get("identifiervalue")
        if not id_type:
            for key, kind in SEARCH_KEYS:
                if data.get(key):
                    id_type, id_value = kind, data[key]
                    break
        found = policy.search_policies(id_type, id_value)
        return ok(
            None if found else "No policies found",
            policies=found,
            identifiertype=id_type,
            identifiervalue=id_value,
        )


class ClaimListView(SendingView):
    def get(self, request, facility_external_id):
        qs = Claim.objects.filter(facility=self.facility).order_by("-id")
        q = request.query_params
        if q.get("status"):
            qs = qs.filter(status=q["status"])
        if q.get("stage"):
            qs = qs.filter(stage=q["stage"])
        if q.get("search"):
            term = q["search"].strip()
            qs = qs.filter(
                Q(claim_no__icontains=term)
                | Q(beneficiary_name__icontains=term)
                | Q(member_id__icontains=term)
                | Q(abha_number__icontains=term)
                | Q(payer_name__icontains=term)
            )
        try:
            limit = min(max(int(q.get("limit") or 20), 1), CLAIM_LIST_LIMIT)
            offset = max(int(q.get("offset") or 0), 0)
        except ValueError:
            return refused("limit and offset must be numbers.")
        return Response(
            {
                "count": qs.count(),
                "results": [row(c) for c in qs[offset : offset + limit]],
            }
        )

    @refusals
    def post(self, request, facility_external_id):
        data = request.data or {}
        encounter = _encounter(self.facility, data.get("encounter"))
        patient = (
            encounter.patient
            if encounter
            else _patient(self.facility, data.get("patient"))
        )
        if isinstance(data.get("policy"), dict):
            claim, message = policy.open_case(
                self.facility,
                data["policy"],
                data.get("identifiertype") or data.get("id_type"),
                data.get("identifiervalue") or data.get("id_value"),
                patient=patient,
            )
        elif data.get("payer_code") or data.get("id_type"):
            claim = eligibility.discover(
                self.facility,
                data.get("payer_code"),
                data.get("id_type"),
                data.get("id_value"),
                {
                    k: data.get(k)
                    for k in ("aadhaar_number", "mobile_number", "member_id")
                },
                patient=patient,
            )
            message = ELIGIBILITY_QUEUED
        else:
            raise ServiceRefusal("Choose a policy to open the claim with.")
        if encounter is not None:
            claim.encounter = encounter
            claim.save(update_fields=["encounter", "modified_date"])
        return ok(message, claim)


class ClaimStateView(SendingView):
    def get(self, request, facility_external_id, claim_id):
        try:
            claim = self.claim(claim_id)
        except Http404:
            return Response({"error": NO_SUCH_CLAIM}, status=http.HTTP_404_NOT_FOUND)
        return Response(claim_state(claim))


class EligibilityView(SendingView):
    @refusals
    def post(self, request, facility_external_id, claim_id):
        claim = self.claim(claim_id)
        data = request.data or {}
        extra = {k: data[k] for k in ("aadhaar_number", "mobile_number") if data.get(k)}
        eligibility.run_check(
            claim,
            data.get("purpose"),
            data.get("policy_code", claim.policy_code),
            data.get("member_id", claim.member_id),
            extra=extra or None,
        )
        return ok(ELIGIBILITY_QUEUED, claim)


class AuthRequirementsView(SendingView):
    @refusals
    def post(self, request, facility_external_id, claim_id):
        claim = self.claim(claim_id)
        eligibility.request_auth(claim)
        return ok(AUTH_SENT, claim)


class PlanView(SendingView):
    @refusals
    def post(self, request, facility_external_id, claim_id):
        claim = self.claim(claim_id)
        refresh = (request.data or {}).get("refresh") in (True, "true", "1", 1)
        ack = plan.request_plan(claim, refresh=refresh)
        return ok(PLAN_REUSED if ack is None else PLAN_REQUESTED, claim)


class LinesView(NhcxFacilityView):
    @refusals
    def post(self, request, facility_external_id, claim_id):
        claim = self.claim(claim_id)
        data = request.data or {}
        line, message = lines.add_line(
            claim, data.get("kind"), data.get("code"), data.get("parent_code")
        )
        if data.get("quantity") not in (None, "", 1, "1"):
            lines.update_lines(
                claim, [{"id": str(line.external_id), "quantity": data["quantity"]}]
            )
            line.refresh_from_db()
        return ok(message, claim, line=row(line))

    @refusals
    def put(self, request, facility_external_id, claim_id):
        claim = self.claim(claim_id)
        changes = (request.data or {}).get("lines")
        if not isinstance(changes, list):
            raise ServiceRefusal("Send the lines to update.")
        return ok(lines.update_lines(claim, changes), claim)


class LineDetailView(NhcxFacilityView):
    @refusals
    def delete(self, request, facility_external_id, claim_id, line_id):
        claim = self.claim(claim_id)
        return ok(lines.remove_line(claim, line_id), claim)


class AdmissionView(NhcxFacilityView):
    @refusals
    def post(self, request, facility_external_id, claim_id):
        claim = self.claim(claim_id)
        encounter = (request.data or {}).get("encounter")
        if not encounter:
            return ok(lines.unlink_admission(claim), claim)
        return ok(lines.link_admission(claim, encounter), claim)

    @refusals
    def delete(self, request, facility_external_id, claim_id):
        claim = self.claim(claim_id)
        return ok(lines.unlink_admission(claim), claim)


class LedgerView(NhcxFacilityView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not request.user.is_superuser:
            raise PermissionDenied("Only administrators can read the gateway ledger.")

    def get(self, request, facility_external_id, entry_id=None):
        ledger = get_gateway().ledger
        try:
            if entry_id is None:
                try:
                    limit = int(request.query_params.get("limit") or 50)
                except ValueError:
                    limit = 50
                return Response({"results": ledger.list(limit)})
            entry = ledger.get(entry_id)
        except GatewayError as e:
            return refused(f"{e.code}: {e.message}")
        if entry is None:
            return Response({"error": "No such entry"}, status=http.HTTP_404_NOT_FOUND)
        return Response(entry)
