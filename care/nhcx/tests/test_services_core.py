from decimal import Decimal

from care.nhcx.gateway.errors import GatewayError, SendError
from care.nhcx.models import (
    ClaimAuth,
    ClaimLine,
    ClaimPlan,
    ClaimPlanBenefit,
    ClaimPreauth,
)
from care.nhcx.services import (
    _gather,
    common,
    eligibility,
    hooks,
    lines,
    plan,
    policy,
    polling,
    stage,
    state,
)
from care.nhcx.services.common import ServiceRefusal
from care.nhcx.tests.core_helpers import (
    OWN_CODE,
    PAYER_CODE,
    NhcxCoreTestBase,
    bundle,
)


class HookTests(NhcxCoreTestBase):
    def tearDown(self):
        for name in hooks.DEFAULTS:
            hooks.unregister(name)
        super().tearDown()

    def test_defaults_answer_until_registered(self):
        claim = self.make_claim()
        saved = dict(hooks._registry)  # noqa: SLF001
        hooks._registry.clear()  # noqa: SLF001
        self.addCleanup(hooks._registry.update, saved)  # noqa: SLF001
        self.assertEqual(
            hooks.call("next_send", claim, "preauth"), {"refused": "not available yet"}
        )
        self.assertEqual(hooks.call("enhancement_lines", claim), [])
        self.assertEqual(hooks.call("required_forms", claim, "claim"), [])

    def test_registered_and_failing_hooks(self):
        claim = self.make_claim()
        saved = dict(hooks._registry)  # noqa: SLF001
        self.addCleanup(hooks._registry.update, saved)  # noqa: SLF001
        hooks.register("next_send", lambda c, leg: "preauth")
        self.assertEqual(hooks.call("next_send", claim, "preauth"), "preauth")

        def boom(c, leg):
            msg = "nope"
            raise ValueError(msg)

        hooks.register("next_send", boom)
        self.assertEqual(hooks.call("next_send", claim, "x"), {"refused": "nope"})
        with self.assertRaises(KeyError):
            hooks.register("unknown", boom)


class PolicyTests(NhcxCoreTestBase):
    def test_search_refusals(self):
        with self.assertRaisesMessage(
            ServiceRefusal, "Choose what kind of identifier you are searching with."
        ):
            policy.search_policies("Passport", "1")
        with self.assertRaisesMessage(
            ServiceRefusal, "Enter an identifier value to search for."
        ):
            policy.search_policies("MemberId", "  ")

    def test_search_normalises_and_handles_errors(self):
        self.gw.policies_answer = {
            "status": 200,
            "body": [{"memberid": "M1", "name": "Ravi", "payerid": PAYER_CODE}],
        }
        found = policy.search_policies("MemberId", "M1")
        self.assertEqual(found[0]["member_id"], "M1")
        self.assertEqual(found[0]["raw"]["memberid"], "M1")
        self.gw.policies_answer = GatewayError("REGISTRY", "No policies found")
        self.assertEqual(policy.search_policies("MemberId", "M1"), [])
        self.gw.policies_answer = {"status": 500, "body": {"error": "Registry down"}}
        with self.assertRaisesMessage(ServiceRefusal, "Registry down"):
            policy.search_policies("MemberId", "M1")

    def test_open_case(self):
        with self.assertRaisesMessage(
            ServiceRefusal,
            "That policy has no member ID; a claim cannot be raised without one.",
        ):
            policy.open_case(self.facility, {"name": "x"}, "MemberId", "x")
        claim, message = policy.open_case(
            self.facility, {"memberid": "M1", "name": "Ravi"}, "MemberId", "M1"
        )
        self.assertEqual(message, f"Claim {claim.claim_no} opened.")
        self.assertEqual(claim.status, "draft")
        self.assertEqual((claim.stage, claim.sub_stage), ("eligibility", "draft"))


class EligibilityTests(NhcxCoreTestBase):
    def test_refusals(self):
        claim = self.make_claim()
        cases = [
            (
                ("bogus", "P", "M"),
                "Choose whether this check is a validation, a benefits check or a "
                "discovery.",
            ),
            (
                ("validation", "P", ""),
                "Member ID is required for an eligibility check.",
            ),
            (
                ("validation", "", "M"),
                "Policy code is required for a validation check.",
            ),
            (
                ("benefits", "", "M"),
                "Policy code is required for a benefits check.",
            ),
        ]
        for args, message in cases:
            with (
                self.subTest(message),
                self.assertRaisesMessage(ServiceRefusal, message),
            ):
                eligibility.run_check(claim, *args)
        self.profile.participant_code = ""
        self.profile.save()
        with self.assertRaisesMessage(ServiceRefusal, eligibility.NO_PARTICIPANT):
            eligibility.run_check(claim, "validation", "P", "M")
        self.profile.hfr_id = ""
        self.profile.save()
        with self.assertRaisesMessage(ServiceRefusal, eligibility.NO_HFR):
            eligibility.run_check(claim, "validation", "P", "M")
        self.assertEqual(self.gw.sent, [])

    def test_check_sent(self):
        claim = self.make_claim(abha_number="91-1234-1234-1234")
        ack = eligibility.run_check(claim, "validation", "POL-1", "PMJAY123")
        claim.refresh_from_db()
        self.assertEqual(claim.status, "checking")
        self.assertEqual(claim.txn_id, ack.txn_id)
        self.assertEqual(claim.correlation_id, ack.correlation_id)
        self.assertEqual((claim.stage, claim.sub_stage), ("eligibility", "checking"))
        path, env = self.gw.sent[0]
        self.assertEqual(path, eligibility.PATH)
        self.assertEqual(env["jwe_headers"]["x-hcx-recipient_code"], PAYER_CODE)
        self.assertEqual(env["jwe_headers"]["x-hcx-sender_code"], OWN_CODE)
        self.assertEqual(env["jwe_headers"]["x-hcx-ben-abha-id"], "91-1234-1234-1234")

    def test_send_failure_keeps_ids(self):
        claim = self.make_claim()
        self.gw.results.append(
            SendError(
                "GATEWAY_HTTP_500",
                "NHCX is down",
                ledger_id="txn-failed",
                headers={
                    "x-hcx-correlation_id": "corr-failed",
                    "x-hcx-api_call_id": "api-failed",
                },
            )
        )
        with self.assertRaisesMessage(ServiceRefusal, "NHCX is down"):
            eligibility.run_check(claim, "validation", "POL-1", "PMJAY123")
        claim.refresh_from_db()
        self.assertEqual(claim.status, "error")
        self.assertEqual(claim.txn_id, "txn-failed")
        self.assertEqual(claim.correlation_id, "corr-failed")
        self.assertEqual(claim.error_message, "NHCX is down")

    def test_refusal_before_ids(self):
        claim = self.make_claim()
        self.gw.results.append(SendError("CONFIG", "No key for the payer"))
        with self.assertRaisesMessage(ServiceRefusal, "No key for the payer"):
            eligibility.run_check(claim, "validation", "POL-1", "PMJAY123")
        claim.refresh_from_db()
        self.assertEqual(claim.status, "draft")

    def test_not_ok_result(self):
        claim = self.make_claim()

        def refused(path, envelope):
            r = self.gw.ok_result(path, envelope)
            r.ok, r.error_code, r.error_message = False, "ERR_X", "bad request"
            return r

        self.gw.results.append(refused)
        with self.assertRaisesMessage(ServiceRefusal, "ERR_X: bad request"):
            eligibility.run_check(claim, "validation", "POL-1", "PMJAY123")
        claim.refresh_from_db()
        self.assertEqual(claim.status, "error")
        self.assertTrue(claim.txn_id)

    def test_discover_opens_case(self):
        with self.assertRaisesMessage(
            ServiceRefusal, "An Aadhaar number has 12 digits"
        ):
            eligibility.discover(
                self.facility,
                PAYER_CODE,
                "MobileNo",
                "9999999999",
                {"aadhaar_number": "12"},
            )
        claim = eligibility.discover(
            self.facility, PAYER_CODE, "MobileNo", "9999999999"
        )
        claim.refresh_from_db()
        self.assertEqual(claim.purpose, "discovery")
        self.assertEqual(claim.status, "checking")

    def test_auth_requirements_refusals_and_send(self):
        claim = self.make_claim()
        with self.assertRaisesMessage(
            ServiceRefusal,
            "Check the policy's eligibility before validating a procedure set "
            "against it.",
        ):
            eligibility.request_auth(claim)
        claim.status = "eligible"
        claim.save()
        with self.assertRaisesMessage(
            ServiceRefusal,
            "Choose the line items first, this checks the procedure set, so there "
            "has to be one.",
        ):
            eligibility.request_auth(claim)
        ClaimLine.objects.create(
            claim=claim, kind="Procedure", code="MG0111A", unit_price=100, amount=100
        )
        self.profile.hfr_id = ""
        self.profile.save()
        with self.assertRaisesMessage(ServiceRefusal, eligibility.NO_ORG_AUTH):
            eligibility.request_auth(claim)
        self.profile.hfr_id = "IN3410000001"
        self.profile.save()
        ack = eligibility.request_auth(claim)
        ruling = ClaimAuth.objects.get(claim=claim)
        self.assertEqual(ruling.status, "checking")
        self.assertEqual(ruling.correlation_id, ack.correlation_id)
        self.assertEqual(ruling.asked_codes, eligibility.fingerprint(claim))

    def test_ensure_auth_requirements(self):
        claim = self.make_claim(status="eligible")
        ClaimLine.objects.create(claim=claim, kind="Procedure", code="X1")
        # the generic adapter does not ask unprompted
        self.assertFalse(eligibility.ensure_auth_requirements(claim.external_id))
        self.assertFalse(ClaimAuth.objects.filter(claim=claim).exists())


class PlanTests(NhcxCoreTestBase):
    def test_request_and_reuse(self):
        claim = self.make_claim()
        ack = plan.request_plan(claim)
        row = ClaimPlan.objects.get(claim=claim)
        self.assertEqual(row.status, "fetching")
        self.assertEqual(row.txn_id, ack.txn_id)
        self.assertEqual(row.provider_id, "IN3410000001")

        row.status = "ready"
        row.save()
        ClaimPlanBenefit.objects.create(plan=row, code="MG1", kind="Procedure", rate=10)
        other = self.make_claim()
        self.assertIsNone(plan.request_plan(other))
        copied = ClaimPlan.objects.get(claim=other)
        self.assertEqual(copied.status, "ready")
        self.assertEqual(copied.benefits.get().code, "MG1")
        self.assertIsNotNone(plan.request_plan(other, refresh=True))

    def test_refusals(self):
        claim = self.make_claim()
        self.profile.hfr_id = ""
        self.profile.save()
        with self.assertRaisesMessage(ServiceRefusal, "HFR ID"):
            plan.request_plan(claim)


class LineTests(NhcxCoreTestBase):
    def setUp(self):
        super().setUp()
        self.claim = self.make_claim(status="eligible")
        self.plan = ClaimPlan.objects.create(claim=self.claim, status="ready")
        ClaimPlanBenefit.objects.create(
            plan=self.plan,
            seq=1,
            code="MG004A",
            kind="Procedure",
            rate=0,
            extras=[
                {
                    "type": "Stratification",
                    "code": "STRAT6a",
                    "label": "Ward",
                    "rate": 1800,
                }
            ],
        )
        ClaimPlanBenefit.objects.create(
            plan=self.plan, seq=2, code="ST009B", kind="Procedure", rate=50000
        )
        ClaimPlanBenefit.objects.create(
            plan=self.plan,
            seq=3,
            code="MG004A",
            kind="Procedure",
            category_code="MP",
            category_display="Paediatric",
            rate=0,
            extras=[
                {
                    "type": "Stratification",
                    "code": "STRAT6a",
                    "label": "Ward",
                    "rate": 1800,
                }
            ],
        )
        ClaimPlanBenefit.objects.create(
            plan=self.plan, seq=4, code="OPEN1", kind="Procedure", rate=0
        )

    def test_add_refusals(self):
        cases = [
            (("Room", "X"), "That is not something a preauth can quote."),
            (("Procedure", ""), "Nothing was selected."),
            (("Procedure", "NOPE"), "NOPE is not a procedure in this plan."),
            (("Implant", "NOPE"), "NOPE is not a implant in this plan."),
            (
                ("Stratification", "STRAT6a"),
                "Pick the procedure this ward tier belongs to.",
            ),
            (
                ("Stratification", "STRAT9", "MG004A"),
                "That ward tier is not offered for this package.",
            ),
        ]
        for args, message in cases:
            with (
                self.subTest(message),
                self.assertRaisesMessage(ServiceRefusal, message),
            ):
                lines.add_line(self.claim, *args)
        self.plan.status = "fetching"
        self.plan.save()
        with self.assertRaisesMessage(ServiceRefusal, lines.PLAN_NOT_READY):
            lines.add_line(self.claim, "Procedure", "ST009B")

    def test_add_update_remove(self):
        line, message = lines.add_line(self.claim, "Procedure", "ST009B")
        self.assertEqual(message, "ST009B added.")
        self.assertEqual(line.unit_price, Decimal("50000.00"))
        with self.assertRaisesMessage(
            ServiceRefusal, "ST009B is already on this preauth."
        ):
            lines.add_line(self.claim, "Procedure", "ST009B")
        tier, _ = lines.add_line(self.claim, "Stratification", "STRAT6a", "MG004A")
        self.assertEqual((tier.unit_price, tier.parent_code), (Decimal(1800), "MG004A"))
        open_line, _ = lines.add_line(self.claim, "Procedure", "OPEN1")
        tiered, _ = lines.add_line(self.claim, "Procedure", "MG004A")
        lines.update_lines(
            self.claim, [{"id": str(tiered.external_id), "unit_price": "999"}]
        )
        tiered.refresh_from_db()
        self.assertEqual(tiered.unit_price, Decimal(0))

        lid = str(line.external_id)
        for qty, message in [
            ("1.5", "The quantity of ST009B must be a whole number."),
            ("0", "Enter a quantity for ST009B."),
            ("x", "Enter a quantity for ST009B."),
        ]:
            with self.subTest(qty), self.assertRaisesMessage(ServiceRefusal, message):
                lines.update_lines(self.claim, [{"id": lid, "quantity": qty}])
        oid = str(open_line.external_id)
        with self.assertRaisesMessage(ServiceRefusal, "Enter a price for OPEN1."):
            lines.update_lines(self.claim, [{"id": oid, "unit_price": "abc"}])
        with self.assertRaisesMessage(
            ServiceRefusal, "The price of OPEN1 cannot be negative."
        ):
            lines.update_lines(self.claim, [{"id": oid, "unit_price": "-1"}])
        self.assertEqual(
            lines.update_lines(
                self.claim,
                [
                    {"id": lid, "quantity": "2", "unit_price": "1"},
                    {"id": oid, "unit_price": "250.5", "quantity": ""},
                ],
            ),
            "Lines updated.",
        )
        line.refresh_from_db()
        open_line.refresh_from_db()
        self.assertEqual(line.amount, Decimal("100000.00"))
        self.assertEqual(open_line.amount, Decimal("250.50"))
        self.assertEqual(
            lines.remove_line(self.claim, line.external_id), "Line removed."
        )
        self.assertFalse(ClaimLine.objects.filter(id=line.id).exists())

    def test_category_is_picked(self):
        line, _ = lines.add_line(self.claim, "Procedure", "MG004A", category_code="MP")
        self.assertEqual(
            (line.category_code, line.category_display), ("MP", "Paediatric")
        )
        tier, _ = lines.add_line(self.claim, "Stratification", "STRAT6a", "MG004A")
        self.assertEqual(tier.category_code, "MP")
        picked = _gather._benefits(self.plan, self.claim)  # noqa: SLF001
        self.assertEqual([b.category_code for b in picked], ["MP"])

    def test_link_admission_refusals(self):
        claim = self.make_claim(status="checking")
        with self.assertRaisesMessage(ServiceRefusal, lines.NOT_ELIGIBLE_LINK):
            lines.link_admission(claim, "x")
        with self.assertRaisesMessage(ServiceRefusal, lines.NOT_A_MATCH):
            lines.link_admission(self.claim, "00000000-0000-0000-0000-000000000000")


class StageTests(NhcxCoreTestBase):
    def test_stage_follows_legs(self):
        claim = self.make_claim(status="eligible")
        self.assertEqual(stage.recompute(claim), ("eligibility", "eligible"))
        ClaimPreauth.objects.create(
            claim=claim, status="submitting", submission_kind="enhancement"
        )
        claim.refresh_from_db()
        self.assertEqual(stage.recompute(claim), ("enhancement", "requested"))
        claim.refresh_from_db()
        self.assertEqual(claim.stage, "enhancement")


class PollingTests(NhcxCoreTestBase):
    def checking_claim(self):
        claim = self.make_claim()
        eligibility.run_check(claim, "validation", "POL-1", "PMJAY123")
        claim.refresh_from_db()
        return claim

    def test_reply_found_is_applied(self):
        claim = self.checking_claim()
        self.gw.ledger.add_reply(
            claim.txn_id,
            "in-1",
            self.envelope(
                bundle("eligibility-response-generic.json"), claim.correlation_id
            ),
        )
        self.assertEqual(polling.poll_all(claim), [])
        claim.refresh_from_db()
        self.assertEqual(claim.status, "eligible")
        self.assertEqual(claim.beneficiary_name, "Ravi Kumar")

    def test_own_reply_is_skipped(self):
        claim = self.checking_claim()
        self.gw.ledger.add_reply(
            claim.txn_id,
            "in-1",
            self.envelope(
                bundle("eligibility-response-generic.json"), claim.correlation_id
            ),
            sender=OWN_CODE.upper(),
        )
        polling.poll_all(claim)
        claim.refresh_from_db()
        self.assertEqual(claim.status, "checking")

    def test_not_found_writes_error(self):
        claim = self.checking_claim()
        polling.poll_all(claim)
        claim.refresh_from_db()
        self.assertEqual(claim.status, "error")
        self.assertEqual(claim.error_message, polling.LEGS["eligibility"].not_found)

    def test_dispatch_failed(self):
        claim = self.checking_claim()
        self.gw.ledger.related_rows[claim.txn_id] = []
        self.gw.ledger.dispatches[claim.txn_id] = {
            "status": "dispatch_failed",
            "errorMessage": "Payer unreachable",
        }
        polling.poll_all(claim)
        claim.refresh_from_db()
        self.assertEqual(
            (claim.status, claim.error_message), ("error", "Payer unreachable")
        )

    def test_protocol_rejection(self):
        claim = self.checking_claim()
        self.gw.ledger.related_rows[claim.txn_id] = []
        self.gw.ledger.rows = [
            {
                "id": "p-1",
                "direction": "in",
                "type": "coverageeligibility",
                "created_at": None,
            }
        ]
        self.gw.ledger.envelopes["p-1"] = {
            "fhir": {
                "type": "ProtocolResponse",
                "x-hcx-correlation_id": claim.correlation_id,
                "x-hcx-status": "response.error",
                "x-hcx-error_details": {"code": "ERR_SIG", "message": "Bad signature"},
            }
        }
        polling.poll_all(claim)
        claim.refresh_from_db()
        self.assertEqual(claim.error_message, "ERR_SIG: Bad signature")

    def test_other_errors_become_notes(self):
        claim = self.checking_claim()
        self.gw.ledger.related_rows[claim.txn_id] = GatewayError(
            "LEDGER_IO", "disk full"
        )
        notes = polling.poll_all(claim)
        self.assertEqual(len(notes), 1)
        self.assertIn("disk full", notes[0])
        claim.refresh_from_db()
        self.assertEqual(claim.status, "checking")

    def test_peer_refusal_on_preauth(self):
        claim = self.make_claim(status="eligible")
        row = ClaimPreauth.objects.create(
            claim=claim,
            status="submitting",
            submission_kind="preauth",
            txn_id="t-pa",
            correlation_id="c-pa",
        )
        self.gw.ledger.related_rows["t-pa"] = [
            {"id": "t-pa", "direction": "out", "status": "dispatched"},
            {"id": "t-peer", "direction": "out", "status": "failed"},
        ]
        self.gw.ledger.entries["t-peer"] = {
            "peer": {"response": {"error": {"code": "ERR_X", "message": "bad bundle"}}}
        }
        polling.poll_preauth(claim)
        row.refresh_from_db()
        self.assertEqual(row.status, "error")
        self.assertEqual(
            row.error_message,
            "The payer answered, but NHCX refused its reply: ERR_X: bad bundle "
            "Nothing more will arrive on this thread, submit again to open a new one.",
        )
        claim.refresh_from_db()
        self.assertEqual((claim.stage, claim.sub_stage), ("preauth", "refused"))

    def test_cancel_not_found(self):
        claim = self.make_claim(status="eligible")
        row = ClaimPreauth.objects.create(
            claim=claim,
            status="cancelling",
            cancel_txn_id="t-c",
            cancel_correlation_id="c-c",
        )
        polling.poll_cancel(claim)
        row.refresh_from_db()
        self.assertEqual(
            (row.status, row.error_message), ("error", polling.CANCEL_GONE)
        )


class StateTests(NhcxCoreTestBase):
    KEYS = {
        "claim",
        "plan",
        "benefits",
        "admissions",
        "lines",
        "ruling",
        "required_documents",
        "forms",
        "documents",
        "stage",
        "sub_stage",
        "preauth",
        "preauth_items",
        "next_send",
        "adapter",
        "desk",
        "predeterminations",
        "enhancement_lines",
        "queries",
        "submission",
        "submission_items",
        "payments",
        "paid_total",
        "enquiries",
        "poll_notes",
    }

    def test_shape(self):
        claim = self.make_claim(status="eligible")
        ClaimPlan.objects.create(claim=claim, status="ready")
        ClaimLine.objects.create(claim=claim, kind="Implant", code="I1", seq=1)
        ClaimLine.objects.create(claim=claim, kind="Procedure", code="P1", seq=2)
        out = state.claim_state(claim)
        self.assertTrue(set(out) >= self.KEYS)
        self.assertEqual(out["claim"]["id"], str(claim.external_id))
        self.assertEqual(out["claim"]["facility_id"], str(self.facility.external_id))
        self.assertEqual([ln["code"] for ln in out["lines"]], ["P1", "I1"])
        self.assertEqual(out["plan"]["status"], "ready")
        self.assertEqual(set(out["next_send"]), {"preauth", "claim"})
        self.assertEqual(set(out["required_documents"]), {"preauth", "claim"})
        self.assertEqual(out["paid_total"], 0.0)
        self.assertEqual(out["poll_notes"], [])
        self.assertIsNone(out["submission"])
        self.assertIsInstance(out["adapter"], str)

    def test_admissions_match_abha(self):
        from care.nhcx.models.abha import set_abha

        patient = self.create_patient(name="Ravi")
        set_abha(patient, number="91-1234-1234-1234")
        org = self.create_facility_organization(facility=self.facility)
        enc = self.create_encounter(patient, self.facility, org)
        enc.encounter_class = "imp"
        enc.status = "in_progress"
        enc.period = {"start": "2026-01-02T10:00:00+05:30"}
        enc.save()
        claim = self.make_claim(status="eligible", abha_number="91-1234-1234-1234")
        found = state.admissions(claim)
        self.assertEqual([a["id"] for a in found], [str(enc.external_id)])
        self.assertEqual(
            lines.link_admission(claim, enc.external_id),
            "Admission linked to the claim.",
        )
        claim.refresh_from_db()
        self.assertEqual(claim.encounter_id, enc.id)
        self.assertEqual(str(claim.admission_date), "2026-01-02")
        self.assertEqual(claim.patient_id, patient.id)
        self.assertEqual(state.admissions(self.make_claim(abha_number="")), [])


class AbdmHipIdFallbackTests(NhcxCoreTestBase):
    def setUp(self):
        super().setUp()
        self.profile.hfr_id = None
        self.profile.save()

    def health_facility(self, hf_id):
        from django.apps import apps

        try:
            model = apps.get_model("abdm", "HealthFacility")
        except LookupError:
            self.skipTest("care_abdm plug is not installed")
        return model.objects.create(facility=self.facility, hf_id=hf_id)

    def test_no_plug_value_keeps_blank(self):
        self.assertEqual(common.abdm_hf_id(self.facility), "")
        self.assertIsNone(common.facility_profile(self.facility).hfr_id)

    def test_blank_hfr_id_uses_abdm_hip_id(self):
        self.health_facility("IN3410000077")
        self.assertEqual(common.abdm_hf_id(self.facility), "IN3410000077")
        self.assertEqual(common.facility_profile(self.facility).hfr_id, "IN3410000077")
        self.assertEqual(
            common.facility_input(self.facility).identifier_value, "IN3410000077"
        )
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.hfr_id)

    def test_profile_hfr_id_wins(self):
        self.health_facility("IN3410000077")
        self.profile.hfr_id = "IN3410000001"
        self.profile.save()
        self.assertEqual(common.facility_profile(self.facility).hfr_id, "IN3410000001")
