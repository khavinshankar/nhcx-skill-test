import json
from pathlib import Path

from django.test import SimpleTestCase

from care.nhcx.fhir.inputs import FhirBuildError
from care.nhcx.fhir.read import (
    claim_response,
    communication,
    eligibility,
    payment,
    plan,
)

FIXTURES = Path(__file__).parent / "fixtures" / "bundles"


def load(name):
    return json.loads((FIXTURES / name).read_text())


class EligibilityReadTests(SimpleTestCase):
    def test_verdict_pmjay(self):
        verdict = eligibility.read_verdict(load("eligibility-auth-response-pmjay.json"))
        self.assertEqual(verdict["status"], "eligible")
        self.assertTrue(verdict["inforce"])
        self.assertTrue(verdict["auth_required"])
        self.assertEqual(verdict["allowed_amount"], 2070)
        self.assertEqual(verdict["beneficiary_name"], "PALLVI")
        self.assertEqual(
            verdict["patient_address"], "ISPUR, UNA, HIMACHAL PRADESH, 177202"
        )
        self.assertEqual(verdict["plan_name"], "PMJAY for Himachal")
        self.assertEqual(verdict["relationship"], "Child")
        self.assertEqual(verdict["abha_number"], "91-0000-0000-0000")

    def test_verdict_wallet(self):
        verdict = eligibility.read_verdict(load("eligibility-benefits-response.json"))
        self.assertEqual(verdict["allowed_amount"], 500000)
        self.assertEqual(verdict["used_amount"], 0)
        self.assertNotIn("plan_name", verdict)

    def test_ruling_pmjay(self):
        ruling = eligibility.read(load("eligibility-auth-response-pmjay.json"))["auth"]
        self.assertEqual([i["code"] for i in ruling["items"]], ["MG0111A", "MG072C"])
        self.assertEqual(ruling["items"][0]["allowed_amount"], 2070)
        forms = [r for r in ruling["requirements"] if r["kind"] == "form"]
        self.assertEqual(
            forms[0]["form_url"], "https://payer.gov.in/policy/questionnaire/100003"
        )
        self.assertTrue(forms[0]["at_preauth"])
        self.assertEqual(ruling["requirements"][0]["stage"], "pre")
        self.assertEqual(ruling["requirements"][0]["for_code"], "MG0111A")

    def test_ruling_generic_stages(self):
        ruling = eligibility.read_auth(load("eligibility-response-generic.json"))
        by_code = {r["code"]: r for r in ruling["requirements"]}
        self.assertTrue(by_code["POI"]["at_preauth"])
        self.assertEqual(by_code["HDS"]["stage"], "post")
        self.assertFalse(by_code["HDS"]["at_preauth"])
        self.assertEqual(by_code["STG"]["kind"], "form")
        self.assertEqual(ruling["items"][0]["benefit_type"], "benefit")

    def test_requirement_text(self):
        self.assertEqual(
            eligibility.parse_requirement_text("Type: Pre\n Procedure Code:MG0111A"),
            ("", "pre", "MG0111A"),
        )

    def test_no_response(self):
        self.assertEqual(eligibility.read_verdict({"entry": []}), {})


class PlanReadTests(SimpleTestCase):
    def test_pmjay_plan(self):
        out = plan.read(load("plan-response-pmjay.json"))
        self.assertEqual(out["plan"]["plan_identifier"], "100155-HOSP2P146514")
        self.assertEqual(out["plan"]["plan_title"], "PMJAY - Universal Health Policy")
        self.assertEqual(out["plan"]["sum_insured"], 500000)
        self.assertEqual(out["plan"]["status"], "ready")
        self.assertEqual(out["plan"]["policy_documents"][0]["code"], "ADN")
        first = out["benefits"][0]
        self.assertEqual(
            (first["code"], first["kind"], first["rate"]), ("MG004A", "Procedure", 0)
        )
        self.assertEqual(first["cost_type"], "Procedure")
        self.assertEqual(first["category_code"], "MG")
        self.assertEqual(first["conditions"]["ProcedureType"], "Conservative")
        self.assertEqual(first["extras"][0]["code"], "STRAT006a")
        self.assertEqual(first["extras"][0]["rate"], 1800)
        self.assertEqual(first["supporting_info"][0]["code"], "MAND0409")
        codes = [b["code"] for b in out["benefits"]]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(
            [f["kind"] for f in out["forms"]], ["questionnaire", "questionnaire"]
        )

    def test_generic_plan_with_coverage_limits(self):
        out = plan.read(load("plan-response-generic.json"))
        self.assertEqual(out["plan"]["plan_type"], "Hospitalisation Indemnity Policy")
        rows = {b["code"]: b for b in out["benefits"]}
        self.assertEqual(rows["PROC-KNEE-01"]["rate"], 150000)
        self.assertEqual(
            rows["PROC-KNEE-01"]["conditions"]["ProcedureType"], "Surgical"
        )
        self.assertEqual(rows["49122002"]["extras"][0]["type"], "fullcoverage")
        self.assertIsNone(rows["49122002"]["kind"])
        self.assertEqual(rows["710967003"]["kind"], "Procedure")
        self.assertEqual(rows["710967003"]["rate"], 90)
        self.assertEqual(
            [b["seq"] for b in out["benefits"]], list(range(1, len(rows) + 1))
        )
        form = out["forms"][0]
        self.assertEqual(
            form["url"], "https://kyro.care/fhir/Questionnaire/PROC-PED-05"
        )
        self.assertEqual(form["items"][0]["depth"], 0)
        self.assertTrue(form["items"][0]["required"])

    def test_empty(self):
        out = plan.read({"resourceType": "Bundle", "entry": []})
        self.assertEqual(out["plan"]["status"], "empty")
        self.assertIn("no InsurancePlan", out["plan"]["message"])

    def test_nested_items_and_options(self):
        bundle = {
            "entry": [
                {
                    "resource": {
                        "resourceType": "Questionnaire",
                        "url": "https://p/Questionnaire/Q1",
                        "item": [
                            {
                                "linkId": "g",
                                "type": "group",
                                "text": "Group",
                                "item": [
                                    {
                                        "linkId": "c",
                                        "type": "choice",
                                        "prefix": "1.",
                                        "answerOption": [
                                            {"valueString": "A"},
                                            {
                                                "valueCoding": {
                                                    "code": "b",
                                                    "display": "B",
                                                },
                                                "initialSelected": True,
                                            },
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                },
                {
                    "resource": {
                        "resourceType": "Questionnaire",
                        "url": "https://p/Questionnaire/Q1",
                    }
                },
            ]
        }
        forms = plan.read_forms(bundle)
        self.assertEqual(len(forms), 1)
        self.assertEqual(forms[0]["title"], "https://p/Questionnaire/Q1")
        child = forms[0]["items"][1]
        self.assertEqual((child["depth"], child["text"]), (1, "1."))
        self.assertEqual((child["options"], child["initial"]), (["A", "B"], "B"))


class ClaimResponseReadTests(SimpleTestCase):
    def test_approved(self):
        out = claim_response.read(load("preauth-approved-wf21.json"))
        self.assertEqual(
            (out["outcome"], out["adjudication"], out["status"]),
            ("complete", "approved", "approved"),
        )
        self.assertEqual(out["preauth_ref"], "CL/26/0SE000108")
        self.assertEqual(out["approved_amount"], 150000)
        self.assertEqual(out["items_json"][0]["sequence"], 1)
        self.assertEqual(out["error_message"], "")

    def test_acknowledgement_and_query_trail(self):
        out = claim_response.read(load("preauth-received-wf20-pmjay.json"))
        self.assertEqual(out["status"], "submitting")
        self.assertNotIn("null", out["query_note"].split("\n"))
        self.assertIn(
            "Request acknowledged and accepted for further processing.",
            out["query_note"],
        )

    def test_queried_and_rejected(self):
        self.assertEqual(
            claim_response.read(load("preauth-queried-wf24.json"))["status"], "queried"
        )
        rejected = claim_response.read(load("preauth-rejected-wf23-pmjay.json"))
        self.assertEqual(
            (rejected["outcome"], rejected["status"]), ("error", "rejected")
        )
        self.assertEqual(
            claim_response.read(load("claim-rejected-wf291.json"))["status"], "rejected"
        )

    def test_deduction(self):
        out = claim_response.read(load("claim-approved-deduction-wf26-pmjay.json"))
        self.assertEqual(out["approved_amount"], 2430)
        self.assertEqual(out["submitted_amount"], 2700)

    def test_workflow_id_wins_but_error_and_partial_hold(self):
        response = {"resourceType": "ClaimResponse", "outcome": "complete"}
        bundle = {"entry": [{"resource": response}]}
        self.assertEqual(
            claim_response.read(bundle, workflow_id="24")["status"], "queried"
        )
        self.assertEqual(
            claim_response.read(bundle, workflow_id="NM-1")["status"], "approved"
        )
        self.assertEqual(
            claim_response.read(
                bundle, workflow_id="21", status_header="response.error"
            )["status"],
            "error",
        )
        partial = {
            "entry": [
                {"resource": {"resourceType": "ClaimResponse", "outcome": "partial"}}
            ]
        }
        # C5P: partial only when verdict_status is partial (reason approved)
        self.assertEqual(
            claim_response.read(partial, workflow_id="21")["status"], "approved"
        )
        partial["entry"][0]["resource"]["adjudication"] = [
            {
                "category": {"coding": [{"code": "status"}]},
                "reason": {"coding": [{"code": "Approved"}]},
            }
        ]
        self.assertEqual(
            claim_response.read(partial, workflow_id="21")["status"], "partial"
        )

    def test_table(self):
        cases = [
            ("queued", "approved", "submitting"),
            ("complete", "submitted", "submitting"),
            ("complete", "cancelled", "rejected"),
            ("complete", "rejected", "rejected"),
            ("error", "denied", "rejected"),
            ("complete", "queried", "queried"),
            ("error", "", "error"),
            ("partial", "approved", "partial"),
            ("partial", "pending", "queried"),
            ("complete", "", "approved"),
            ("complete", "pending", "queried"),
            ("", "", "queried"),
        ]
        for outcome, reason, status in cases:
            with self.subTest(outcome=outcome, reason=reason):
                self.assertEqual(claim_response.decide(outcome, reason), status)

    def test_error_message(self):
        bundle = {
            "entry": [
                {
                    "resource": {
                        "resourceType": "ClaimResponse",
                        "outcome": "complete",
                        "disposition": "Could not process",
                        "error": [
                            {
                                "code": {
                                    "coding": [{"code": "E1", "display": "Bad item"}]
                                }
                            }
                        ],
                    }
                }
            ]
        }
        out = claim_response.read(bundle)
        self.assertEqual(out["status"], "error")
        self.assertEqual(out["error_message"], "E1: Bad item\nCould not process")

    def test_query_pieces(self):
        self.assertEqual(
            claim_response.clean_pieces(" : null|USER~1~Other~send xray~Trust| : .|-"),
            ["USER~1~Other~send xray~Trust"],
        )

    def test_protocol_response(self):
        out = claim_response.read(
            {
                "type": "ProtocolResponse",
                "x-hcx-error_details": {"code": "E", "message": "No"},
            }
        )
        self.assertTrue(out["refused"])
        self.assertEqual(out["error_message"], "E: No")

    def test_predetermination(self):
        out = claim_response.read_predetermination(load("preauth-approved-wf21.json"))
        self.assertEqual(out["status"], "answered")
        self.assertEqual(out["allowed_amount"], 150000)


class TaskReplyReadTests(SimpleTestCase):
    def test_cancel_accepted(self):
        out = claim_response.read_task_reply(
            load("task-cancelled-wfPC02.json"), "cancel"
        )
        self.assertTrue(out["accepted"])
        self.assertEqual(out["task_status"], "completed")
        self.assertIsNotNone(out["response"])

    def test_reprocess_reopened(self):
        out = claim_response.read_task_reply(
            load("task-reprocess-wf37.json"), "reprocess"
        )
        self.assertEqual(out["answer"], "reopened")
        self.assertTrue(out["detail"])

    def test_status_from_header_output_and_rejection(self):
        bundle = {
            "entry": [
                {
                    "resource": {
                        "resourceType": "Task",
                        "status": "completed",
                        "description": "Status",
                    }
                }
            ]
        }
        header = json.dumps(
            {"entity_status": "approved", "stage": "preauth", "total_paid": 0}
        )
        out = claim_response.read_task_reply(
            bundle, "status", {"x-hcx-status_response": header}
        )
        self.assertEqual(out["answer"], "approved")
        self.assertEqual(out["detail"], "Status; stage: preauth; total_paid: 0")
        with_output = {
            "entry": [
                {
                    "resource": {
                        "resourceType": "Task",
                        "status": "completed",
                        "output": [
                            {
                                "type": {"coding": [{"code": "claimStatus"}]},
                                "valueString": "queried",
                            }
                        ],
                    }
                }
            ]
        }
        self.assertEqual(
            claim_response.read_task_reply(with_output, "status")["answer"], "queried"
        )
        rejected = {
            "entry": [{"resource": {"resourceType": "Task", "status": "rejected"}}]
        }
        self.assertEqual(
            claim_response.read_task_reply(rejected, "status")["answer"], "not-found"
        )

    def test_cancel_refused_on_error(self):
        bundle = {
            "entry": [
                {
                    "resource": {
                        "resourceType": "Task",
                        "status": "completed",
                        "output": [{"valueReference": {"reference": "urn:uuid:r"}}],
                    }
                },
                {
                    "fullUrl": "urn:uuid:r",
                    "resource": {"resourceType": "ClaimResponse", "outcome": "error"},
                },
            ]
        }
        self.assertFalse(claim_response.read_task_reply(bundle, "cancel")["accepted"])


class CommunicationReadTests(SimpleTestCase):
    def test_query(self):
        out = communication.read(load("communication-query-wf24.json"))
        self.assertEqual(out["kind"], "query")
        self.assertEqual(out["reason_code"], "additionalinfo")
        self.assertEqual(out["intent"], "order")
        self.assertEqual(out["claim_ref"], "NM-26-0SE00002I")
        self.assertEqual(out["request_id"], "4b35a6eb-3f99-5d0c-b0c8-5b2f049fdbde")
        self.assertEqual(
            out["questions"], ["Share the pre-operative X-ray and the clinical notes."]
        )
        self.assertIn("urn:uuid:c1a17d6e-c718-58de-8d3d-fd4c0607d729", out["refs"])

    def test_notification(self):
        bundle = load("communication-notification-wfN02-pmjay.json")
        out = communication.read(bundle)
        self.assertEqual(out["kind"], "notification")
        self.assertEqual(out["remarks"], "Required Message for the provider")
        self.assertTrue(out["request_id"])
        self.assertEqual(communication.handler_for(bundle), "request")

    def test_classification(self):
        self.assertEqual(
            communication.classify("order", "", "resubmit"), "notification"
        )
        self.assertEqual(communication.classify("proposal", "query"), "notification")
        self.assertEqual(communication.classify("", "questionnaire"), "query")
        self.assertEqual(communication.classify("", "grievance"), "notification")
        self.assertEqual(
            communication.reason_code(
                {"reasonCode": [{"coding": [{"code": "claimArbitartion"}]}]}
            ),
            "claimarbitration",
        )

    def test_note(self):
        bundle = {
            "entry": [
                {
                    "fullUrl": "urn:uuid:n1",
                    "resource": {
                        "resourceType": "Communication",
                        "identifier": [{"value": "NM-1"}],
                        "payload": [{"contentString": "Payment soon"}],
                    },
                }
            ]
        }
        self.assertEqual(communication.handler_for(bundle), "note")
        out = communication.read_note(bundle)
        self.assertEqual(
            (out["kind"], out["claim_ref"], out["request_id"]), ("note", "NM-1", "n1")
        )
        self.assertEqual(communication.read(bundle), {})


class PaymentReadTests(SimpleTestCase):
    def test_notice(self):
        out = payment.read(load("payment-notice-wf30.json"))
        self.assertEqual(out["claim_ref"], "NM-26-0SE00002L")
        self.assertEqual(out["amount"], 135000)
        self.assertEqual(out["payment_status"], "cleared")
        self.assertEqual(out["payment_date"], "2026-09-10")
        self.assertEqual(out["utr"], "UTR1789064619092")
        self.assertEqual(
            [(d["seq"], d["type_code"], d["amount"]) for d in out["details"]],
            [(1, "TDS", 15000), (2, "Payment", 135000)],
        )

    def test_pmjay_notice(self):
        out = payment.read(load("payment-notice-tds-wf30-pmjay.json"))
        self.assertEqual(out["claim_ref"], "EO26AA2700001")
        self.assertEqual(out["disposition"], "Payment initiated")
        self.assertEqual(
            out["details"][0]["reference"], "PMJAY/HP/S/2024/R2/10000009/TDS"
        )

    def test_not_a_notice(self):
        with self.assertRaisesMessage(FhirBuildError, "That is not a payment notice."):
            payment.read({"entry": [{"resource": {"resourceType": "Task"}}]})
