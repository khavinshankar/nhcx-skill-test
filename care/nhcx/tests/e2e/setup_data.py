"""Idempotent HMIS test data for the e2e runs (``nhcx_e2e setup``).

Creates, through CARE's own APIs as a superuser: a test facility with its NHCX
profile (HFR id, the application's participant code), an operator holding a
role at that facility (the GUI and CLI sign in as them), a doctor with an HPR
id, and per test payer a patient carrying the ABHA number the registry
returns for the member, admitted (an in-progress inpatient encounter).
"""

from __future__ import annotations

import secrets
import string
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from care.nhcx.tests.e2e import config as cfg

FACILITY_NAME = "NHCX E2E Hospital"
OPERATOR = "nhcx_e2e_operator"
DOCTOR = "nhcx_e2e_doctor"
OPERATOR_ROLE = "Facility Admin"
DOCTOR_ROLE = "Doctor"


def _password() -> str:
    alphabet = string.ascii_letters + string.digits
    body = "".join(secrets.choice(alphabet) for _ in range(14))
    return f"E2e@{body}9"


def _superuser():
    from care.users.models import User

    user = User.objects.filter(is_superuser=True, deleted=False).order_by("id").first()
    if user is None:
        msg = "No superuser in this database; create one first."
        raise RuntimeError(msg)
    return user


def _fixture_base():
    from care.fixtures.base import CareFixtureBase

    client = APIClient()
    sup = _superuser()
    client.force_authenticate(user=sup)
    base = CareFixtureBase(client)
    base.user = sup
    return base


def _geo_org():
    from care.emr.models import Organization

    org = (
        Organization.objects.filter(org_type="govt", parent__isnull=True)
        .order_by("id")
        .first()
    )
    if org is None:
        msg = "No government organisation in this database to place the facility in."
        raise RuntimeError(msg)
    return org


def _facility(base, geo, log):
    from care.facility.models import Facility

    found = Facility.objects.filter(name=FACILITY_NAME, deleted=False).first()
    if found:
        return found
    made = base.create_facility(
        str(geo.external_id), name=FACILITY_NAME, is_public=False
    )
    log(f"created facility {FACILITY_NAME}")
    return Facility.objects.get(external_id=made["id"])


def registry_hfr(code):
    """The HFR id the registry holds for the participant: PMJAY refuses any other (PAYR-1008)."""
    from care.nhcx.gateway import get_gateway

    raw = get_gateway().default_client.fetch_participant(code).get("raw") or {}
    return raw.get("registry_id") or ""


def _profile(facility, conf):
    from care.nhcx.gateway import get_gateway
    from care.nhcx.models import FacilityProfile

    codes = get_gateway().participant_codes
    code = (codes() if callable(codes) else codes)[0]
    profile, _ = FacilityProfile.objects.update_or_create(
        facility=facility,
        defaults={
            "hfr_id": conf.get("NHCX_TEST_HFR_ID") or registry_hfr(code),
            "participant_code": code,
        },
    )
    return profile


def _root_org(facility):
    from care.emr.models import FacilityOrganization

    return (
        FacilityOrganization.objects.filter(facility=facility, parent__isnull=True)
        .order_by("id")
        .first()
    )


def _user(base, geo, facility, username, role_name, password, log):
    from care.emr.models.organization import FacilityOrganizationUser
    from care.security.models import RoleModel
    from care.users.models import User

    user = User.objects.filter(username=username).first()
    if user is None:
        base.create_user(
            str(geo.external_id),
            username=username,
            password=password,
            first_name="NHCX E2E",
            last_name="Doctor" if username == DOCTOR else "Operator",
        )
        user = User.objects.get(username=username)
        log(f"created user {username}")
    if password:
        user.set_password(password)
        user.save(update_fields=["password"])
    org = _root_org(facility)
    role = RoleModel.objects.get(name=role_name)
    if not FacilityOrganizationUser.objects.filter(
        organization=org, user=user
    ).exists():
        base.add_user_to_facility_organization(
            str(facility.external_id),
            str(org.external_id),
            str(user.external_id),
            str(role.external_id),
        )
        log(f"gave {username} the role {role_name} at {FACILITY_NAME}")
    return user


def _doctor_profile(user, conf):
    from care.nhcx.models import PractitionerProfile

    PractitionerProfile.objects.update_or_create(
        user=user,
        defaults={
            "hpr_id": conf.get("NHCX_TEST_HPR_ID"),
            "qualification_display": "MBBS",
            "active": True,
        },
    )


def _patient(base, geo, facility, label, policy, log):
    """A patient carrying the beneficiary's ABHA number, admitted at the facility."""
    from care.emr.models import Encounter, Patient
    from care.nhcx.models.abha import find_patients_by_abha, set_abha

    abha = policy.get("abha_number") or ""
    name = f"NHCX E2E {label} Beneficiary"
    patient = find_patients_by_abha(abha).order_by("id").first() if abha else None
    if patient is None:
        patient = Patient.objects.filter(name=name, deleted=False).first()
    if patient is None:
        extra = {}
        mobile = (policy.get("mobile_number") or "").strip()[-10:]
        if len(mobile) == 10 and mobile.isdigit():  # noqa: PLR2004
            extra["phone_number"] = f"+91{mobile}"
        made = base.create_patient(
            str(geo.external_id), name=name, gender="male", **extra
        )
        patient = Patient.objects.get(external_id=made["id"])
        log(f"created patient {name}")
    if abha:
        set_abha(patient, number=abha)
    open_encounter = (
        Encounter.objects.filter(
            patient=patient,
            facility=facility,
            encounter_class="imp",
            status="in_progress",
        )
        .order_by("-id")
        .first()
    )
    if open_encounter is None:
        start = (timezone.now() - timedelta(days=1)).isoformat()
        base.create_encounter(
            str(patient.external_id),
            str(facility.external_id),
            status="in_progress",
            encounter_class="imp",
            priority="routine",
            period={"start": start},
        )
        log(f"admitted {name}")
    return patient


def _policy(member_id, payer):
    from care.nhcx.services import policy

    rows = policy.search_policies("MemberId", member_id) or []
    return next(
        (r for r in rows if r.get("payer_id") == payer), rows[0] if rows else {}
    )


def run(log=print) -> dict:
    """Creates what is missing; returns ids and writes the .env values it owns."""
    conf = cfg.load()
    base = _fixture_base()
    geo = _geo_org()
    facility = _facility(base, geo, log)
    _profile(facility, conf)
    password = conf.get("NHCX_TEST_PASSWORD") or _password()
    operator = _user(base, geo, facility, OPERATOR, OPERATOR_ROLE, password, log)
    doctor = _user(base, geo, facility, DOCTOR, DOCTOR_ROLE, _password(), log)
    _doctor_profile(doctor, conf)
    patients = {}
    for label, member, payer in (
        ("IRDAI", "NHCX_TEST_IRDAI_MEMBER_ID", "NHCX_TEST_IRDAI_PAYER"),
        ("PMJAY", "NHCX_TEST_PMJAY_MEMBER_ID", "NHCX_TEST_PMJAY_PAYER"),
    ):
        if not conf.get(member):
            log(f"{label}: {member} unset, no patient made")
            continue
        found = _policy(conf.get(member), conf.get(payer))
        patients[label] = str(
            _patient(base, geo, facility, label, found, log).external_id
        )
    values = {
        "NHCX_TEST_FACILITY": str(facility.external_id),
        "NHCX_TEST_USER": OPERATOR,
        "NHCX_TEST_PASSWORD": password,
        "NHCX_TEST_DOCTOR": DOCTOR,
    }
    for key, value in values.items():
        if conf.get(key) != value:
            cfg.write_env_value(key, value)
    return {
        "facility": str(facility.external_id),
        "operator": operator.username,
        "doctor": doctor.username,
        "patients": patients,
    }
