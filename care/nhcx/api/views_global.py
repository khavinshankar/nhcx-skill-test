"""NHCX routes outside facility scope (api/CONTRACT.md): the D2 practitioner
profile (S16) and the server-side A19 ABHA flow (S13-S15)."""

from __future__ import annotations

from django.http import Http404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from care.nhcx.api.views_core import ok, refusals
from care.nhcx.models import PractitionerProfile
from care.nhcx.services import abha
from care.nhcx.services.common import ServiceRefusal

PRACTITIONER_SAVED = "Practitioner saved."
PRACTITIONER_UPDATED = "Practitioner updated."
NOT_YOURS = "You can only change your own practitioner profile."
NO_PATIENT = "No such patient."
PATIENT_DENIED = "You do not have access to this patient."
PRACTITIONER_FIELDS = (
    "prefix",
    "identifier_type_code",
    "identifier_type_display",
    "hpr_id",
    "qualification_code",
    "qualification_display",
    "role_code",
    "role_display",
    "specialty_code",
    "specialty_display",
    "department",
)


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def _user(user_id, current):
    from care.users.models import User

    if user_id in {"me", "self"}:
        return current
    users = User.objects.all()
    found = (
        users.filter(id=int(user_id)).first()
        if user_id.isdigit()
        else users.filter(external_id=user_id).first()
        if len(user_id) == 36  # noqa: PLR2004
        else users.filter(username=user_id).first()
    )
    if found is None:
        raise Http404
    return found


def _profile_json(user, found):
    out = {
        "user_id": str(user.external_id),
        "username": user.username,
        "name": user.get_full_name() if hasattr(user, "get_full_name") else "",
        "active": bool(found.active) if found else True,
    }
    for k in PRACTITIONER_FIELDS:
        out[k] = _s(getattr(found, k, "")) if found else ""
    return out


class PractitionerProfileView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, user_id):
        user = _user(user_id, request.user)
        found = PractitionerProfile.objects.filter(user=user).first()
        return ok(None, profile=_profile_json(user, found))

    def put(self, request, user_id):
        user = _user(user_id, request.user)
        if user.id != request.user.id and not request.user.is_superuser:
            raise PermissionDenied(NOT_YOURS)
        data = request.data
        found = PractitionerProfile.objects.filter(user=user).first()
        created = found is None
        found = found or PractitionerProfile(user=user)
        for k in PRACTITIONER_FIELDS:
            if k in data:
                value = _s(data.get(k))
                field = PractitionerProfile._meta.get_field(k)  # noqa: SLF001
                if value or not field.has_default():
                    setattr(found, k, value or None)
        if "active" in data:
            found.active = _s(data.get("active")).lower() not in {"false", "0", "no"}
        found.save()
        return ok(
            PRACTITIONER_SAVED if created else PRACTITIONER_UPDATED,
            profile=_profile_json(user, found),
        )


def _patient(request, patient_id):
    from care.emr.models import Patient
    from care.security.authorization import AuthorizationController

    found = Patient.objects.filter(external_id=_s(patient_id) or None).first()
    if found is None:
        raise ServiceRefusal(NO_PATIENT)
    if not AuthorizationController.call("can_write_patient_obj", request.user, found):
        raise PermissionDenied(PATIENT_DENIED)
    return found


def _answer(result, default=None):
    """``ok`` with the service's own ``message`` (the ABHA service's text)."""
    result = dict(result or {})
    return ok(result.pop("message", None) or default, **result)


class AbhaView(APIView):
    """A19: one route per step; the answer carries ``txn_id`` and never a token."""

    permission_classes = (IsAuthenticated,)

    @refusals
    def get(self, request, action):
        if action == "certificate":
            held = abha.certificate()
            return ok(
                None, public_key=held["public_key"], expires_at=held["expires_at"]
            )
        if action == "suggestions":
            return _answer(
                abha.suggestions(request.user, _s(request.GET.get("txn_id")))
            )
        raise Http404

    @refusals
    def post(self, request, action):  # noqa: PLR0911
        d = request.data
        user = request.user
        txn = _s(d.get("txn_id"))
        if action == "certificate":
            return self.get(request, action)
        if action == "aadhaar-otp":
            return _answer(abha.enrol_otp(user, d.get("aadhaar"), txn or None))
        if action == "aadhaar-verify":
            return _answer(abha.enrol_verify(user, txn, d.get("otp"), d.get("mobile")))
        if action == "suggestions":
            return _answer(abha.suggestions(user, txn))
        if action == "address":
            return _answer(abha.enrol_address(user, txn, d.get("abha_address")))
        if action == "mobile-otp":
            return _answer(
                abha.login_otp(user, _s(d.get("abha_no")), _s(d.get("mobile"))),
            )
        if action == "mobile-verify":
            return _answer(abha.login_verify(user, txn, d.get("otp")))
        if action == "profile":
            return _answer(abha.profile(user, txn, _s(d.get("abha_no")) or None))
        if action == "link":
            patient = _patient(request, d.get("patient"))
            return _answer(abha.link(user, txn, patient), "ABHA linked to the patient.")
        raise Http404
