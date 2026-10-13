import json
from datetime import date
from pathlib import Path

from django.test import SimpleTestCase

from care.nhcx.fhir.build import (
    claim,
    communication,
    coverage_request,
    organization,
    patient,
    payment_ack,
    plan_task,
    practitioner,
    questionnaire_response,
    task,
)
from care.nhcx.fhir.codes import PROFILES
from care.nhcx.fhir.inputs import FhirBuildError, PatientInput
from care.nhcx.tests import fhir_samples as s

FIXTURES = Path(__file__).parent / "fixtures" / "bundles"
BASE = "https://nhcx.abdm.gov.in"


def load(name):
    return json.loads((FIXTURES / name).read_text())


def layout(bundle):
    return [(e["fullUrl"], e["resource"]["resourceType"]) for e in bundle["entry"]]


def anchor(bundle):
    return bundle["entry"][0]["resource"]


class EligibilityRequestTests(SimpleTestCase):
    def test_bundle_per_purpose(self):
        ids = {
            "validation": "coverage-validation-request-generic",
            "benefits": "coverage-benefits-request-generic",
            "discovery": "coverage-discovery-request-generic",
            "auth-requirements": "coverage-authrequirements-request-generic",
        }
        for purpose, bundle_id in ids.items():
            with self.subTest(purpose=purpose):
                out = coverage_request.build(s.eligibility_input(purpose))
                self.assertEqual(out["id"], bundle_id)
                self.assertEqual(
                    out["meta"]["profile"],
                    [PROFILES["CoverageEligibilityRequestBundle"]],
                )
                request = anchor(out)
                self.assertEqual(request["resourceType"], "CoverageEligibilityRequest")
                self.assertEqual(request["purpose"], [purpose])
                self.assertEqual(
                    out["entry"][0]["fullUrl"], f"{BASE}/coverage-eligibility/request"
                )
                self.assertTrue(
                    all(e["fullUrl"].startswith(BASE) for e in out["entry"])
                )
                self.assertEqual(
                    "item" in request, purpose in ("benefits", "auth-requirements")
                )

    def test_tier_rides_on_its_procedure(self):
        request = anchor(
            coverage_request.build(s.eligibility_input("auth-requirements"))
        )
        self.assertEqual(len(request["item"]), 1)
        item = request["item"][0]
        self.assertEqual(item["productOrService"]["coding"][0]["code"], "MG0111A")
        self.assertEqual(item["modifier"][0]["coding"][0]["code"], "STRAT006a")

    def test_refusals(self):
        with self.assertRaisesMessage(FhirBuildError, "is not a coverage eligibility"):
            coverage_request.build(s.eligibility_input("nonsense"))
        with self.assertRaisesMessage(FhirBuildError, "member id"):
            coverage_request.build(
                s.eligibility_input(
                    patient=PatientInput(), coverage=s.CoverageInput(policy_code="P")
                )
            )
        facility = s.facility()
        facility.identifier_value = ""
        with self.assertRaisesMessage(FhirBuildError, "registry id"):
            coverage_request.build(s.eligibility_input(facility=facility))

    def test_matches_example_layout(self):
        example = load("eligibility-auth-request.json")
        out = coverage_request.build(s.eligibility_input("auth-requirements"))
        self.assertEqual(out["id"], example["id"])
        self.assertEqual(
            anchor(out)["resourceType"], example["entry"][0]["resource"]["resourceType"]
        )


class PlanTaskTests(SimpleTestCase):
    def test_inputs(self):
        out = plan_task.build("POL-001", "IN2910000001")
        self.assertEqual(out["id"], "insurance-request-generic")
        self.assertEqual(layout(out), [(f"{BASE}/insurance/request", "Task")])
        inputs = anchor(out)["input"]
        self.assertEqual(
            [(i["type"]["coding"][0]["code"], i["valueString"]) for i in inputs],
            [("policyNumber", "POL-001"), ("providerId", "IN2910000001")],
        )
        self.assertEqual(anchor(out)["code"]["coding"][0]["code"], "poll")

    def test_refusal(self):
        with self.assertRaises(FhirBuildError):
            plan_task.build("", "")


class ClaimTests(SimpleTestCase):
    def test_bundle_per_kind(self):
        anchors = {
            "preauth": (
                "preauth-request-generic",
                "/preauth/request",
                "preauthorization",
            ),
            "enhancement": (
                "preauth-enhancement-request-generic",
                "/preauth/enhancement",
                "preauthorization",
            ),
            "preauth-queryupdate": (
                "preauth-queryupdate-request-generic",
                "/preauth/queryupdate",
                "preauthorization",
            ),
            "predetermination": (
                "predetermination-request-generic",
                "/predetermination/request",
                "predetermination",
            ),
            "claim": ("claim-request-generic", "/claim/request", "claim"),
            "claim-queryupdate": (
                "claim-queryupdate-request-generic",
                "/claim/queryupdate",
                "claim",
            ),
        }
        for kind, (bundle_id, path, use) in anchors.items():
            with self.subTest(kind=kind):
                out = claim.build(s.claim_input(kind))
                self.assertEqual(out["id"], bundle_id)
                self.assertEqual(out["meta"]["profile"], [PROFILES["ClaimBundle"]])
                self.assertEqual(out["entry"][0]["fullUrl"], BASE + path)
                self.assertEqual(anchor(out)["use"], use)
                self.assertEqual(anchor(out)["meta"]["profile"], [PROFILES["Claim"]])

    def test_preauth_entry_order_and_elements(self):
        out = claim.build(s.claim_input("preauth"))
        self.assertEqual(
            [t for _, t in layout(out)],
            [
                "Claim",
                "Patient",
                "Organization",
                "Organization",
                "Coverage",
                "Practitioner",
                "Procedure",
                "QuestionnaireResponse",
            ],
        )
        c = anchor(out)
        self.assertEqual(c["identifier"][0]["value"], "NM-26-0001")
        self.assertEqual(c["identifier"][0]["type"]["coding"][0]["code"], "CLN")
        self.assertEqual(c["patient"]["reference"], f"{BASE}/patient")
        self.assertEqual(c["insurer"]["reference"], f"{BASE}/payer")
        self.assertEqual(c["provider"]["reference"], f"{BASE}/provider")
        self.assertEqual(c["created"], "2026-09-10T10:30:00+05:30")
        self.assertEqual(c["billablePeriod"]["start"], "2026-09-09T00:00:00+05:30")
        self.assertEqual(
            c["diagnosis"][0]["diagnosisCodeableConcept"]["coding"][0]["code"], "J90"
        )
        self.assertEqual(
            c["procedure"][0]["type"][0]["coding"][0]["display"], "Conservative"
        )
        item = c["item"][0]
        self.assertEqual(len(c["item"]), 1)
        self.assertEqual(item["id"], "Item/1")
        self.assertEqual(item["productOrService"]["coding"][0]["code"], "MG0111A")
        self.assertEqual(item["modifier"][0]["coding"][0]["code"], "STRAT006a")
        self.assertEqual(item["net"], {"value": 3600, "currency": "INR"})
        self.assertEqual(c["total"], {"value": 3600, "currency": "INR"})
        self.assertTrue(all("id" in si for si in c["supportingInfo"]))
        info = [si["category"]["coding"][0]["code"] for si in c["supportingInfo"]]
        self.assertEqual(info[0], "DIA")
        self.assertIn("INF", info)

    def test_documents_follow_leg_stage(self):
        docs = [
            s.document(stage="preauth"),
            s.document(id=12, stage="claim", code="BIL"),
        ]
        pre = anchor(claim.build(s.claim_input("preauth", documents=docs)))
        codes = [
            si.get("code", {}).get("coding", [{}])[0].get("code")
            for si in pre["supportingInfo"]
        ]
        self.assertIn("DIA", codes)
        self.assertNotIn("BIL", codes)

    def test_claim_lama_collapse_and_preauth_ref(self):
        data = s.claim_input(
            "claim",
            documents=[
                s.document(stage="claim"),
                s.document(id=12, stage="claim", code="HDS"),
            ],
            discharge_mode="lama",
            discharge_stage="before surgery",
            discharge_date=date(2026, 9, 11),
            lama_package={
                "display": "LAMA",
                "rate": 500,
                "category_code": "MG",
                "category_display": "General Medicine",
            },
            preauth_ref="PA-1",
        )
        c = anchor(claim.build(data))
        self.assertEqual(c["use"], "claim")
        self.assertEqual(len(c["item"]), 1)
        self.assertEqual(c["item"][0]["productOrService"]["coding"][0]["code"], "LM100")
        self.assertEqual(c["item"][0]["net"]["value"], 1000)
        self.assertEqual(c["insurance"][0]["preAuthRef"], ["PA-1"])
        categories = [si["category"]["coding"][0]["code"] for si in c["supportingInfo"]]
        self.assertIn("DIS", categories)
        codes = [
            si.get("code", {}).get("coding", [{}])[0].get("code")
            for si in c["supportingInfo"]
        ]
        self.assertNotIn("HDS", codes)

    def test_matches_example_claim_shape(self):
        example = anchor(load("claim-request-death-d9.json"))
        c = anchor(claim.build(s.claim_input("claim")))
        for key in (
            "identifier",
            "status",
            "type",
            "use",
            "patient",
            "insurer",
            "provider",
            "item",
            "total",
        ):
            self.assertIn(key, example)
            self.assertIn(key, c)


class TaskTests(SimpleTestCase):
    def test_kinds(self):
        cases = {
            ("cancel", "preauth"): (
                "preauth-cancel-request-generic",
                "/preauth/cancel",
            ),
            ("status", "preauth"): (
                "preauth-status-request-generic",
                "/preauth/status",
            ),
            ("status", "claim"): ("claim-status-request-generic", "/claim/status"),
            ("reprocess", "claim"): (
                "claim-reprocess-request-generic",
                "/claim/reprocess",
            ),
            ("release", "claim"): ("claim-release-request-generic", "/claim/release"),
        }
        for (action, leg), (bundle_id, path) in cases.items():
            with self.subTest(action=action, leg=leg):
                out = task.build(
                    s.task_input(action, leg=leg, reason="partialpayment", amount=100)
                )
                self.assertEqual(out["id"], bundle_id)
                self.assertEqual(out["meta"]["profile"], [PROFILES["TaskBundle"]])
                self.assertEqual(layout(out)[0], (BASE + path, "Task"))
                t = anchor(out)
                self.assertEqual((t["status"], t["intent"]), ("requested", "order"))
                self.assertEqual(
                    t["code"]["coding"][0],
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/financialtaskcode",
                        "code": action,
                    },
                )

    def test_cancel_inputs(self):
        t = anchor(
            task.build(s.task_input("cancel", reason="others", note="Plan changed"))
        )
        self.assertEqual(t["description"], "Plan changed")
        self.assertEqual(
            [i["type"]["coding"][0]["code"] for i in t["input"]],
            ["claimNumber", "intimationNumber"],
        )
        pmjay = anchor(
            task.build(s.task_input("cancel", intimation_type="initimationNumber"))
        )
        self.assertEqual(
            pmjay["input"][1]["type"]["coding"][0]["code"], "initimationNumber"
        )

    def test_release_amount(self):
        t = anchor(
            task.build(s.task_input("release", reason="partialpayment", amount=1500))
        )
        money = [i["valueMoney"] for i in t["input"] if "valueMoney" in i]
        self.assertEqual(money, [{"value": 1500, "currency": "INR"}])

    def test_refusal(self):
        with self.assertRaises(FhirBuildError):
            task.build(s.task_input("explode"))


class PaymentAckTests(SimpleTestCase):
    def test_ack(self):
        out = payment_ack.build("NM-26-0001", s.facility(), s.payer())
        self.assertEqual(out["id"], "payment-notice-ack-generic")
        t = anchor(out)
        self.assertEqual(t["status"], "completed")
        self.assertEqual(t["code"]["coding"][0]["code"], "status")
        self.assertEqual(
            t["output"][0]["valueCodeableConcept"]["coding"][0]["code"], "paymentack"
        )
        self.assertEqual(t["output"][1]["valueString"], "NM-26-0001")
        example = anchor(load("payment-ack-b7.json"))
        self.assertEqual(example["code"]["coding"][0]["code"], "status")


class ResourceTests(SimpleTestCase):
    def test_patient(self):
        p = patient.build(s.patient())
        self.assertEqual(p["meta"]["profile"], [PROFILES["Patient"]])
        self.assertEqual(
            [i["type"]["coding"][0]["code"] for i in p["identifier"]],
            ["PMJAY", "ABHA", "MB"],
        )
        self.assertEqual(p["birthDate"], "1985-06-15")
        self.assertEqual(p["name"][0]["text"], "Ravi Kumar")

    def test_practitioner(self):
        p = practitioner.build(s.practitioner())
        self.assertEqual(
            [i["type"]["coding"][0]["code"] for i in p["identifier"]],
            ["HPID", "MD", "HPIN"],
        )
        self.assertEqual(p["qualification"][0]["code"]["coding"][0]["code"], "MD")

    def test_organizations(self):
        provider = organization.build_provider(s.facility())
        payer = organization.build_payer(s.payer())
        self.assertEqual(provider["name"], "Sample Hospital")
        self.assertEqual(provider["meta"]["profile"], [PROFILES["Organization"]])
        self.assertEqual(payer["name"], "Sandbox Payer")

    def test_questionnaire_response(self):
        qr = questionnaire_response.build(s.form(), s.claim_input().answers, 1)
        self.assertEqual(qr["questionnaire"], s.form().url)
        self.assertEqual(qr["item"][0]["answer"], [{"valueString": "Breathlessness"}])
        self.assertEqual(qr["item"][1]["answer"], [{"valueBoolean": False}])
        unanswered = s.form()
        unanswered.items = unanswered.items[:1]
        self.assertIsNone(questionnaire_response.build(unanswered, [], 1))
        defaulted = questionnaire_response.build(s.form(), [], 1)
        self.assertEqual(
            defaulted["item"],
            [{"linkId": "2", "text": "Smoker", "answer": [{"valueBoolean": True}]}],
        )


class CommunicationTests(SimpleTestCase):
    def test_reply(self):
        request = load("communication-query-wf24.json")
        sent = claim.build(s.claim_input("preauth"))
        out = communication.build(
            s.reply_input(request_bundle=request, sent_bundle=sent)
        )
        self.assertEqual(out["meta"]["profile"], [PROFILES["TaskBundle"]])
        types = [t for _, t in layout(out)]
        self.assertEqual(types[:3], ["Task", "Communication", "CommunicationRequest"])
        t, comm = out["entry"][0]["resource"], out["entry"][1]["resource"]
        self.assertEqual(
            (t["status"], t["code"]["coding"][0]["code"]), ("completed", "deliver")
        )
        self.assertEqual(
            t["input"][0]["valueReference"]["reference"], out["entry"][1]["fullUrl"]
        )
        self.assertNotIn("inResponseTo", comm)
        self.assertEqual(comm["about"][0]["display"], "Claim NM-26-0001")
        self.assertEqual(comm["payload"][0], {"contentString": "Attached the X-ray."})
        self.assertIn("contentAttachment", comm["payload"][1])
        urls = {e["fullUrl"] for e in out["entry"]}
        self.assertIn(comm["about"][0]["reference"], urls)

    def test_reply_refusals(self):
        with self.assertRaisesMessage(FhirBuildError, "not a question"):
            communication.build_reply(s.reply_input(kind="notification"))
        with self.assertRaisesMessage(FhirBuildError, "empty answer"):
            communication.build_reply(
                s.reply_input(
                    request_bundle=load("communication-query-wf24.json"),
                    reply_text="",
                    documents=[],
                )
            )

    def test_acknowledgement(self):
        request = load("communication-notification-wfN02-pmjay.json")
        out = communication.build(
            s.reply_input(
                kind="notification", request_bundle=request, reply_text="", documents=[]
            )
        )
        first = out["entry"][0]["resource"]
        self.assertEqual(
            (first["resourceType"], first["status"]), ("Task", "completed")
        )
        self.assertEqual(out["type"], "collection")
        self.assertNotEqual(out["id"], request.get("id"))
        self.assertTrue(out["identifier"]["value"])
        self.assertEqual(len(out["entry"]), len(request["entry"]))
