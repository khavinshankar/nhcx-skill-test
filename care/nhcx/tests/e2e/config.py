"""T1 configuration: the environment first, then ``.env`` beside this file, then defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

E2E_DIR = Path(__file__).resolve().parent
CARE_ROOT = E2E_DIR.parents[3]
ENV_FILE = E2E_DIR / ".env"
ARTIFACTS = E2E_DIR / "artifacts"

# references/PAYERS.md, test participants
DEFAULTS = {
    "NHCX_TEST_MODE": "both",
    "NHCX_TEST_APP_URL": "",
    "NHCX_TEST_SLOWMO_MS": "0",
    "NHCX_TEST_BROWSER_CHANNEL": "chromium",
    "NHCX_TEST_IRDAI_PAYER": "1000004957@hcx",
    "NHCX_TEST_IRDAI_MEMBER_ID": "MRAJ2004001",
    "NHCX_TEST_PMJAY_PAYER": "1518@hcx",
    "NHCX_TEST_PMJAY_PLAN_SEED": str(E2E_DIR / "fixtures" / "pmjay-plan.json"),
    "NHCX_TEST_PLAN_WAIT_SECONDS": "120",
    "NHCX_TEST_WAIT_SECONDS": "120",
    "NHCX_TEST_PMJAY_PAYMENT_WAIT_SECONDS": "600",
    "NHCX_TEST_POLL_AFTER_SECONDS": "30",
    "NHCX_TEST_REPORT": "nhcx-plan/e2e.json",
    "NHCX_TEST_HPR_ID": "71-1234-5678-9012",
    "NHCX_TEST_ABDM_FAKE": "1",
}
SECRETS = {"NHCX_TEST_PASSWORD", "NHCX_TEST_PMJAY_SERVICE_TOKEN"}
VARIABLES = (
    "NHCX_TEST_MODE",
    "NHCX_TEST_ONLY",
    "NHCX_TEST_APP_URL",
    "NHCX_TEST_USER",
    "NHCX_TEST_PASSWORD",
    "NHCX_TEST_FACILITY",
    "NHCX_TEST_DOCTOR",
    "NHCX_TEST_DIAGNOSIS",
    "NHCX_TEST_PMJAY_MANUAL_PACKAGE",
    "NHCX_TEST_SLOWMO_MS",
    "NHCX_TEST_BROWSER_CHANNEL",
    "NHCX_TEST_IRDAI_PAYER",
    "NHCX_TEST_IRDAI_MEMBER_ID",
    "NHCX_TEST_IRDAI_POLICY",
    "NHCX_TEST_PMJAY_PAYER",
    "NHCX_TEST_PMJAY_MEMBER_ID",
    "NHCX_TEST_PMJAY_PLAN_SEED",
    "NHCX_TEST_PLAN_WAIT_SECONDS",
    "NHCX_TEST_PMJAY_SERVICE_TOKEN",
    "NHCX_TEST_WAIT_SECONDS",
    "NHCX_TEST_PMJAY_PAYMENT_WAIT_SECONDS",
    "NHCX_TEST_POLL_AFTER_SECONDS",
    "NHCX_TEST_REPORT",
    "NHCX_TEST_HFR_ID",
    "NHCX_TEST_HPR_ID",
    "NHCX_TEST_ABDM_FAKE",
)


def read_env_file(path: Path = ENV_FILE) -> dict:
    out = {}
    if not path.exists():
        return out
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def write_env_value(key: str, value: str, path: Path = ENV_FILE) -> None:
    """Sets one variable in ``.env``, keeping the rest of the file."""
    lines = path.read_text().splitlines() if path.exists() else []
    done = False
    for i, raw in enumerate(lines):
        if raw.split("=", 1)[0].strip() == key:
            lines[i] = f"{key}={value}"
            done = True
    if not done:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n")


@dataclass
class Config:
    values: dict = field(default_factory=dict)

    def get(self, key: str) -> str:
        return (self.values.get(key) or "").strip()

    def int(self, key: str) -> int:
        try:
            return int(self.get(key) or DEFAULTS.get(key, "0"))
        except ValueError:
            return int(DEFAULTS.get(key, "0"))

    @property
    def report_path(self) -> Path:
        p = Path(self.get("NHCX_TEST_REPORT"))
        return p if p.is_absolute() else CARE_ROOT / p

    def shown(self) -> dict:
        return {
            k: ("set" if self.get(k) else "missing") if k in SECRETS else self.get(k)
            for k in VARIABLES
        }

    def report_view(self) -> dict:
        return {
            "irdai_payer": self.get("NHCX_TEST_IRDAI_PAYER"),
            "irdai_member": self.get("NHCX_TEST_IRDAI_MEMBER_ID"),
            "irdai_policy": self.get("NHCX_TEST_IRDAI_POLICY") or "first found",
            "pmjay_payer": self.get("NHCX_TEST_PMJAY_PAYER"),
            "pmjay_member": self.get("NHCX_TEST_PMJAY_MEMBER_ID") or "missing",
            "facility": self.get("NHCX_TEST_FACILITY"),
            "app_url": self.get("NHCX_TEST_APP_URL"),
            "user": self.get("NHCX_TEST_USER"),
            "password": "set" if self.get("NHCX_TEST_PASSWORD") else "missing",
            "pmjay_service_token": (
                "set" if self.get("NHCX_TEST_PMJAY_SERVICE_TOKEN") else "missing"
            ),
            "pmjay_manual_package": self.get("NHCX_TEST_PMJAY_MANUAL_PACKAGE"),
            "wait_seconds": self.int("NHCX_TEST_WAIT_SECONDS"),
            "poll_after_seconds": self.int("NHCX_TEST_POLL_AFTER_SECONDS"),
        }

    def missing_integrator_values(self) -> list:
        return (
            []
            if self.get("NHCX_TEST_PMJAY_MEMBER_ID")
            else ["NHCX_TEST_PMJAY_MEMBER_ID"]
        )


def load(overrides: dict | None = None) -> Config:
    file_values = read_env_file()
    values = {}
    for key in VARIABLES:
        values[key] = (
            os.environ.get(key) or file_values.get(key) or DEFAULTS.get(key, "")
        )
    for key, value in (overrides or {}).items():
        if value not in (None, ""):
            values[key] = value
    return Config(values)
