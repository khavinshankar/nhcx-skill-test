"""The scenarios, one per test (T3 to T19), in tests/INDEX.md order.

Both runners share these definitions: the CLI runner runs ``run(ctx)``; the GUI
runner reads the same list (``nhcx_e2e list --json``) and drives the screens
for the same test, taking the payer's side through the same payer driver.
"""

from __future__ import annotations

import importlib

from care.nhcx.tests.e2e.scenarios.common import Scenario

TESTS = (
    (
        "T3",
        "irdai",
        "IRDAI Policy Search and Eligibility",
        "t03_irdai_policy_and_eligibility",
    ),
    (
        "T4",
        "irdai",
        "IRDAI Insurance Plan and Authorisation Requirements",
        "t04_irdai_plan_and_auth_requirements",
    ),
    ("T5", "irdai", "IRDAI Pre-authorisation Approved", "t05_irdai_preauth_approved"),
    (
        "T6",
        "irdai",
        "IRDAI Pre-authorisation Rejected and Sent Again",
        "t06_irdai_preauth_rejected",
    ),
    ("T7", "irdai", "IRDAI Query Answered", "t07_irdai_query_answered"),
    ("T8", "irdai", "IRDAI Enhancement", "t08_irdai_enhancement"),
    ("T9", "irdai", "IRDAI Status Enquiry and Cancel", "t09_irdai_cancel_and_status"),
    (
        "T10",
        "irdai",
        "IRDAI Claim Approved, Part-approved and Rejected",
        "t10_irdai_claim",
    ),
    ("T11", "irdai", "IRDAI Payment Notice and Acknowledgement", "t11_irdai_payment"),
    (
        "T12",
        "irdai",
        "IRDAI Reprocess and Balance Release",
        "t12_irdai_reprocess_and_release",
    ),
    (
        "T13",
        "pmjay",
        "PMJAY Eligibility, Package Master and Ruling",
        "t13_pmjay_eligibility_and_package_master",
    ),
    (
        "T14",
        "pmjay",
        "PMJAY Pre-authorisation Through the Payer Service",
        "t14_pmjay_preauth_adjudicated",
    ),
    (
        "T15",
        "pmjay",
        "PMJAY Query Answered by Resubmission",
        "t15_pmjay_query_by_resubmission",
    ),
    (
        "T16",
        "pmjay",
        "PMJAY Rejection and Enhancement",
        "t16_pmjay_rejection_and_enhancement",
    ),
    (
        "T17",
        "pmjay",
        "PMJAY Claim Through the Role Walk",
        "t17_pmjay_claim_adjudicated",
    ),
    (
        "T18",
        "pmjay",
        "PMJAY Payment Notice, Status Refusal and Cancel",
        "t18_pmjay_payment_status_cancel",
    ),
    (
        "T19",
        "pmjay",
        "PMJAY Beneficiary Verification and ABHA",
        "t19_pmjay_biometric_and_abha",
    ),
)


def _load(module):
    try:
        return importlib.import_module(f"{__name__}.{module}")
    except ModuleNotFoundError:
        return None


def all_scenarios() -> list:
    out = []
    for tid, payer, title, module in TESTS:
        mod = _load(module)
        out.append(
            Scenario(
                id=tid,
                payer=payer,
                title=title,
                run=getattr(mod, "run", None),
                gui=getattr(mod, "GUI", True),
                notes=(mod.__doc__ or "").strip() if mod else "not written",
            )
        )
    return out


def select(names) -> list:
    """``[]`` is everything; ``irdai``/``pmjay`` select a payer; else ids."""
    found = all_scenarios()
    if not names:
        return found
    wanted = {n.upper() for n in names}
    return [s for s in found if s.id in wanted or s.payer.upper() in wanted]
