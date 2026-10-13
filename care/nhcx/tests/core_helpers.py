"""Fakes and fixtures for the services-core tests (no network)."""

import itertools
import json
from pathlib import Path
from types import SimpleNamespace

from django.core.cache import cache
from django.test import TestCase, override_settings

from care.nhcx.gateway import reset_gateway, set_gateway
from care.nhcx.gateway.errors import GatewayError
from care.nhcx.models import Claim, FacilityProfile, allocate_claim_no
from care.utils.tests.base import CareAPITestBase

BUNDLES = Path(__file__).parent / "fixtures" / "bundles"
OWN_CODE = "1000001234@hcx"
PAYER_CODE = "1000005678@hcx"


def bundle(name: str) -> dict:
    return json.loads((BUNDLES / name).read_text())


class FakeLedger:
    def __init__(self):
        self.related_rows: dict = {}
        self.envelopes: dict = {}
        self.dispatches: dict = {}
        self.entries: dict = {}
        self.rows: list = []

    @staticmethod
    def _raise_if(value):
        if isinstance(value, Exception):
            raise value
        return value

    def related(self, txn_id):
        if txn_id not in self.related_rows:
            raise GatewayError("TXN_NOT_FOUND", f"no transaction {txn_id}")
        return self._raise_if(self.related_rows[txn_id])

    def fhir(self, entry_id):
        return self.envelopes.get(entry_id) or {}

    def dispatch(self, entry_id):
        return self.dispatches.get(entry_id) or {
            "txnId": entry_id,
            "status": "dispatched",
        }

    def get(self, entry_id):
        return self.entries.get(entry_id)

    def list(self, limit=50):
        return self.rows[: int(limit)]

    def add_reply(self, txn_id, reply_id, envelope, *, sender=PAYER_CODE, type_="x"):
        self.related_rows.setdefault(txn_id, [])
        self.related_rows[txn_id].insert(
            0,
            {
                "id": reply_id,
                "direction": "in",
                "status": "received",
                "sender": sender,
                "recipient": OWN_CODE,
                "correlation_id": envelope.get("jwe_headers", {}).get(
                    "x-hcx-correlation_id"
                ),
                "api_call_id": envelope.get("jwe_headers", {}).get("x-hcx-api_call_id"),
                "type": type_,
                "flow": "callback",
                "created_at": "2026-01-01T00:00:00+00:00",
            },
        )
        self.envelopes[reply_id] = envelope


class FakeGateway:
    """What the services use of ``get_gateway()``: send, ledger, registry."""

    def __init__(self):
        self.sent: list = []
        self.results: list = []
        self.ledger = FakeLedger()
        self.policies_answer = {"status": 200, "body": []}
        self.beneficiary = SimpleNamespace(policies_search=self._policies_search)
        self.searches: list = []
        self._ids = itertools.count(1)

    def _policies_search(self, body):
        self.searches.append(body)
        answer = self.policies_answer
        if isinstance(answer, Exception):
            raise answer
        return answer

    def stop(self):
        pass

    def identity_for(self, code):
        return SimpleNamespace(
            fetch_participant=lambda c: {"name": f"Payer {c}", "code": c}
        )

    def ok_result(self, path, envelope):
        n = next(self._ids)
        h = dict(envelope.get("jwe_headers") or {})
        corr = h.get("x-hcx-correlation_id") or f"corr-{n}"
        h.setdefault("x-hcx-correlation_id", corr)
        h["x-hcx-api_call_id"] = f"api-{n}"
        return SimpleNamespace(
            ok=True,
            path=path,
            headers=h,
            response={"timestamp": 1},
            ledger_id=f"txn-{n}",
            txn_id=f"txn-{n}",
            correlation_id=corr,
            api_call_id=f"api-{n}",
            request_id=None,
            error_code=None,
            error_message=None,
        )

    def send(self, path, envelope):
        self.sent.append((path, envelope))
        if self.results:
            result = self.results.pop(0)
            if isinstance(result, Exception):
                raise result
            if callable(result):
                return result(path, envelope)
            return result
        return self.ok_result(path, envelope)


@override_settings(NHCX_ARCHIVE_DIR="", NHCX_DEFAULT_PAYER_CODE=PAYER_CODE)
class NhcxCoreTestBase(CareAPITestBase, TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.gw = FakeGateway()
        set_gateway(self.gw)
        self.addCleanup(reset_gateway)
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.profile = FacilityProfile.objects.create(
            facility=self.facility, hfr_id="IN3410000001", participant_code=OWN_CODE
        )

    def make_claim(self, **kwargs) -> Claim:
        data = {
            "facility": self.facility,
            "claim_no": allocate_claim_no("NM"),
            "member_id": "PMJAY123",
            "policy_code": "POL-1",
            "payer_id": PAYER_CODE,
            "payer_name": "Payer",
            "beneficiary_name": "Ravi Kumar",
            "patient_gender": "male",
            "patient_dob": "1985-06-15",
        }
        data.update(kwargs)
        return Claim.objects.create(**data)

    def envelope(self, fhir, corr, api_call_id="reply-api-1", **headers):
        h = {
            "x-hcx-correlation_id": corr,
            "x-hcx-api_call_id": api_call_id,
            "x-hcx-sender_code": PAYER_CODE,
            "x-hcx-recipient_code": OWN_CODE,
        }
        h.update(headers)
        return {"meta": {}, "jwe_headers": h, "fhir": fhir}
