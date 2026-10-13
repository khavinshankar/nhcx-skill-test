import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from care.emr.models.patient import PatientIdentifierConfig
from care.emr.resources.patient_identifier.spec import IdentifierConfig
from care.nhcx.models import (
    BiometricAuth,
    Claim,
    ClaimAuth,
    ClaimCareTeam,
    ClaimDiagnosis,
    ClaimDocument,
    ClaimLine,
    ClaimPayment,
    ClaimPaymentDetail,
    ClaimPlan,
    ClaimPlanBenefit,
    ClaimPreauth,
    ClaimQuery,
    ClaimStatus,
    ClaimSubmission,
    Counter,
    FacilityProfile,
    LineKind,
    PractitionerProfile,
    PreauthStatus,
    allocate_claim_no,
    format_claim_no,
    next_number,
    next_value,
)
from care.nhcx.models.abha import (
    ABHA_ADDRESS_SYSTEM,
    ABHA_NUMBER_SYSTEM,
    DUPLICATE_ABHA_MESSAGE,
    find_patients_by_abha,
    get_abha_address,
    get_abha_number,
    set_abha,
)
from care.utils.tests.base import CareAPITestBase


class NhcxModelTestBase(CareAPITestBase, TestCase):
    def setUp(self):
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.patient = self.create_patient(name="Ravi", phone_number="+919999999999")

    def make_claim(self, **kwargs):
        data = {
            "facility": self.facility,
            "claim_no": allocate_claim_no("NM"),
            "member_id": "PMJAY123",
        }
        data.update(kwargs)
        return Claim.objects.create(**data)


class TestMigrations(NhcxModelTestBase):
    def test_abha_identifier_configs_seeded_and_valid(self):
        for system in (ABHA_NUMBER_SYSTEM, ABHA_ADDRESS_SYSTEM):
            config = PatientIdentifierConfig.objects.get(
                facility__isnull=True, config__system=system
            )
            self.assertEqual(config.status, "active")
            IdentifierConfig(**config.config)

    def test_profiles(self):
        profile = FacilityProfile.objects.create(
            facility=self.facility, hfr_id="IN0410000183", participant_code="1000@hcx"
        )
        self.assertEqual(self.facility.nhcx_profile, profile)
        self.assertEqual(profile.identifier_system, "https://facility.abdm.gov.in")
        practitioner = PractitionerProfile.objects.create(
            user=self.user, hpr_id="71-0000-0000-0001"
        )
        self.assertTrue(practitioner.active)
        self.assertEqual(self.user.nhcx_practitioner_profile, practitioner)


class TestCounter(NhcxModelTestBase):
    def test_increments_from_one(self):
        self.assertEqual(next_number("t_series"), 1)
        self.assertEqual(next_number("t_series"), 2)
        self.assertEqual(next_value("t_other", "MRN", 5), "MRN00001")
        self.assertEqual(next_value("t_series", "LAB-", 5), "LAB-00003")
        self.assertEqual(Counter.objects.get(name="t_series").value, 3)

    def test_rollback_does_not_use_a_number(self):
        next_number("t_rb")
        try:
            with transaction.atomic():
                next_number("t_rb")
                raise RuntimeError
        except RuntimeError:
            pass
        self.assertEqual(next_number("t_rb"), 2)

    def test_claim_number_format(self):
        self.assertEqual(
            format_claim_no("NM", 1, datetime.date(2026, 9, 10)), "NM-26-0SE000001"
        )
        first = allocate_claim_no("NM", datetime.date(2026, 9, 10))
        second = allocate_claim_no("NM", datetime.date(2026, 9, 10))
        self.assertEqual(len(first), len(second))
        self.assertLess(first, second)


class TestAbha(NhcxModelTestBase):
    def test_roundtrip_and_digits_only_lookup(self):
        set_abha(self.patient, "91-1234-5678-9012", "ravi@sbx")
        self.assertEqual(get_abha_number(self.patient), "91-1234-5678-9012")
        self.assertEqual(get_abha_address(self.patient), "ravi@sbx")
        self.assertEqual(list(find_patients_by_abha("91123456789012")), [self.patient])
        self.assertEqual(list(find_patients_by_abha("91-1234-5678-0000")), [])
        self.patient.refresh_from_db()
        self.assertEqual(len(self.patient.instance_identifiers), 2)

    def test_update_and_remove(self):
        set_abha(self.patient, "91123456789012")
        set_abha(self.patient, "91-1234-5678-9013")
        self.assertEqual(get_abha_number(self.patient), "91-1234-5678-9013")
        set_abha(self.patient, "")
        self.assertIsNone(get_abha_number(self.patient))

    def test_duplicate_refused(self):
        set_abha(self.patient, "91123456789012")
        other = self.create_patient(name="Other", phone_number="+919999999998")
        with self.assertRaisesMessage(ValueError, DUPLICATE_ABHA_MESSAGE):
            set_abha(other, "91-1234-5678-9012")


class TestClaimWithLegs(NhcxModelTestBase):
    def test_claim_with_children(self):
        claim = self.make_claim(patient=self.patient, payer_id="1000@hcx")
        self.assertEqual(claim.status, ClaimStatus.draft)
        self.assertIsNotNone(claim.external_id)

        plan = ClaimPlan.objects.create(claim=claim, status="ready")
        ClaimPlanBenefit.objects.create(
            plan=plan, code="SB039A", kind="Procedure", rate=Decimal(25000)
        )
        ClaimAuth.objects.create(claim=claim)
        ClaimLine.objects.create(
            claim=claim,
            kind=LineKind.Procedure,
            code="SB039A",
            unit_price=Decimal(25000),
            amount=Decimal(25000),
        )
        ClaimDiagnosis.objects.create(claim=claim, icd10_code="K35.8")
        ClaimCareTeam.objects.create(
            claim=claim, practitioner=self.user, role="treating"
        )
        ClaimDocument.objects.create(
            claim=claim, content_type="application/pdf", data=b"%PDF", size=4
        )
        ClaimPreauth.objects.create(claim=claim, correlation_id="corr-1")
        ClaimSubmission.objects.create(claim=claim)
        payment = ClaimPayment.objects.create(claim=claim, correlation_id="pay-1")
        ClaimPaymentDetail.objects.create(payment=payment, amount=Decimal("100.50"))
        ClaimQuery.objects.create(claim=claim)
        ClaimQuery.objects.create(claim=claim)  # null correlation ids may repeat
        BiometricAuth.objects.create(
            patient=self.patient,
            claim=claim,
            payer_code="1000@hcx",
            stage="Preauth",
            method="FINGERPRINT",
        )

        claim.refresh_from_db()
        self.assertEqual(claim.plan.benefits.count(), 1)
        self.assertEqual(claim.preauth.status, PreauthStatus.submitting)
        self.assertEqual(claim.submission.status, "draft")
        self.assertEqual(claim.payments.get().details.get().amount, Decimal("100.50"))
        self.assertEqual(claim.lines.get().quantity, Decimal(1))
        self.assertEqual(claim.documents.get().stage, "preauth")
        self.assertEqual(claim.payments.get().ack_status, "pending")

    def test_unique_line_and_hard_delete(self):
        claim = self.make_claim()
        line = ClaimLine.objects.create(claim=claim, kind="Procedure", code="X1")
        line.delete()
        ClaimLine.objects.create(claim=claim, kind="Procedure", code="X1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ClaimLine.objects.create(claim=claim, kind="Procedure", code="X1")

    def test_claim_no_unique(self):
        claim = self.make_claim()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_claim(claim_no=claim.claim_no)
