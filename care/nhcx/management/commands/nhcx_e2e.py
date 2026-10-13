"""``manage.py nhcx_e2e``: the NHCX end-to-end runner (T2L).

    nhcx_e2e list [ids|irdai|pmjay] [--json | --ids]
    nhcx_e2e check
    nhcx_e2e setup
    nhcx_e2e run [T3 T5 ... | irdai | pmjay] [--mode cli|gui|both] [--headed] [--report PATH]
    nhcx_e2e payer read|decide|lines|pay|case CLAIM ...   (the payer driver, JSON out)
    nhcx_e2e seed-plan CLAIM
    nhcx_e2e free-beneficiary
    nhcx_e2e report-merge FILE                           (GUI entries into the report)
    nhcx_e2e report [ids|irdai|pmjay] [--report PATH]    (summary; exit code as run)
    nhcx_e2e gui-info                                    (test data the GUI runner needs)
    nhcx_e2e gui-lines CLAIM [N]                         (codes a scenario quotes)
    nhcx_e2e gui-trail CLAIM...                          (correlation and ledger ids)

Exit codes for ``run``: 0 every test passed, 1 any failed, 2 any blocked by
configuration or setup.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from care.nhcx.tests.e2e import checks, report
from care.nhcx.tests.e2e import config as cfg

HOST_COMMAND = "care/scripts/nhcx-e2e.sh run {tests} --mode {mode}{headed}"
FE_DIR_HINT = "../care_fe"


class Command(BaseCommand):
    help = __doc__.splitlines()[0]

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="action", required=True)
        ls = sub.add_parser("list")
        ls.add_argument("tests", nargs="*")
        ls.add_argument("--json", action="store_true")
        ls.add_argument("--ids", action="store_true")
        rep = sub.add_parser("report")
        rep.add_argument("tests", nargs="*")
        rep.add_argument("--report")
        sub.add_parser("check")
        sub.add_parser("setup")
        run = sub.add_parser("run")
        run.add_argument("tests", nargs="*")
        run.add_argument("--mode", choices=("cli", "gui", "both"))
        run.add_argument("--headed", action="store_true")
        run.add_argument("--report")
        run.add_argument("--keep-seed", action="store_true")
        payer = sub.add_parser("payer")
        payer.add_argument("act", choices=("read", "decide", "lines", "pay", "case"))
        payer.add_argument("claim")
        payer.add_argument("rest", nargs="*")
        payer.add_argument("--stage", default="preauth")
        payer.add_argument("--remarks", default="")
        seed = sub.add_parser("seed-plan")
        seed.add_argument("claim")
        sub.add_parser("free-beneficiary")
        merge = sub.add_parser("report-merge")
        merge.add_argument("file")
        sub.add_parser("gui-info")
        lines = sub.add_parser("gui-lines")
        lines.add_argument("claim")
        lines.add_argument("n", nargs="?", type=int, default=1)
        trail = sub.add_parser("gui-trail")
        trail.add_argument("claims", nargs="+")

    def handle(self, *args, **opts):
        action = opts["action"].replace("-", "_")
        return getattr(self, f"do_{action}")(opts)

    # ---- list / check / setup ----

    def do_list(self, opts):
        from care.nhcx.tests.e2e.scenarios import select

        chosen = select(opts["tests"])
        if opts["ids"]:
            self.stdout.write(" ".join(s.id for s in chosen))
            return
        rows = [
            {
                "id": s.id,
                "payer": s.payer,
                "title": s.title,
                "written": s.run is not None,
            }
            for s in chosen
        ]
        if opts["json"]:
            self.stdout.write(json.dumps(rows))
            return
        for r in rows:
            mark = "" if r["written"] else "  (not written)"
            self.stdout.write(f"{r['id']:4} {r['payer']:6} {r['title']}{mark}")

    def do_check(self, opts):
        conf = cfg.load()
        rows = checks.run(conf)
        for r in rows:
            self.stdout.write(f"{r['result'].upper():4} {r['check']:24} {r['detail']}")
        missing = conf.missing_integrator_values()
        if missing:
            self.stdout.write("missing integrator values: " + ", ".join(missing))
        report.merge(conf.report_path, conf.report_view(), rows)
        if checks.failed(rows):
            sys.exit(2)

    def do_setup(self, opts):
        from care.nhcx.tests.e2e import setup_data

        made = setup_data.run(log=self.stdout.write)
        self.stdout.write(json.dumps(made, indent=2))

    # ---- run ----

    def _cli(self, conf, chosen, rows) -> list:
        from care.nhcx.tests.e2e.cli.runner import run_one

        entries = []
        for s in chosen:
            if s.run is None:
                entry = _blocked(s.id, "cli", "ours", "scenario not written", "skipped")
            else:
                entry = run_one(conf, s, out=self.stdout.write)
            entries.append(entry)
            report.merge(conf.report_path, conf.report_view(), rows, [entry])
            self.stdout.write(
                f"{s.id} cli {entry['result'].upper()}"
                + (
                    f" ({entry['cause']}: {entry['detail'][:200]})"
                    if entry["detail"]
                    else ""
                )
            )
        return entries

    def do_run(self, opts):
        from care.nhcx.tests.e2e.scenarios import select

        overrides = {}
        if opts.get("report"):
            overrides["NHCX_TEST_REPORT"] = opts["report"]
        conf = cfg.load(overrides)
        mode = opts.get("mode") or conf.get("NHCX_TEST_MODE") or "both"
        names = opts["tests"] or [
            n for n in (conf.get("NHCX_TEST_ONLY") or "").replace(",", " ").split() if n
        ]
        chosen = select(names)
        if not chosen:
            msg = f"no test matches {names}"
            raise CommandError(msg)
        path = conf.report_path
        rows = checks.run(conf)
        for r in rows:
            self.stdout.write(
                f"setup {r['result'].upper():4} {r['check']:22} {r['detail']}"
            )
        if checks.failed(rows):
            entries = [
                _blocked(s.id, runner, "setup", "setup checks failed")
                for s in chosen
                for runner in _runners(mode)
            ]
            report.merge(path, conf.report_view(), rows, entries)
            sys.exit(2)
        entries = []
        if mode in ("cli", "both"):
            entries = self._cli(conf, chosen, rows)
            if not opts.get("keep_seed"):
                _remove_seeds(entries)
        if mode in ("gui", "both"):
            code = self._gui(conf, chosen, opts)
            data = report.read(path)
            gui = {
                t["id"]: t for t in data.get("tests") or [] if t.get("runner") == "gui"
            }
            entries += [gui[s.id] for s in chosen if s.id in gui]
            if code is None:
                sys.exit(2)
        data = report.merge(path, conf.report_view(), rows, [])
        self.stdout.write(f"report {path}: {json.dumps(data['summary'])}")
        _exit_for(entries)

    def do_report(self, opts):
        from care.nhcx.tests.e2e.scenarios import select

        overrides = {"NHCX_TEST_REPORT": opts["report"]} if opts.get("report") else {}
        conf = cfg.load(overrides)
        data = report.merge(conf.report_path, conf.report_view(), None, [])
        ids = {s.id for s in select(opts["tests"])}
        entries = [t for t in data.get("tests") or [] if t.get("id") in ids]
        for e in entries:
            detail = (
                f" ({e.get('cause')}: {e['detail'][:200]})" if e.get("detail") else ""
            )
            self.stdout.write(f"{e['id']} {e['runner']} {e['result'].upper()}{detail}")
        self.stdout.write(f"report {conf.report_path}: {json.dumps(data['summary'])}")
        _exit_for(entries)

    def _gui(self, conf, chosen, opts):
        """Starts the Playwright runner where it can; else prints the command."""
        tests = " ".join(s.id for s in chosen)
        fe = Path(conf.get("NHCX_TEST_FE_DIR") or (cfg.CARE_ROOT / FE_DIR_HINT))
        if not (fe / "playwright.config.ts").exists() or not shutil.which("npx"):
            self.stdout.write(
                "The GUI runner runs where the screens and the browser are (the host). "
                "Run:\n  "
                + HOST_COMMAND.format(
                    tests=tests,
                    mode="gui",
                    headed=" --headed" if opts["headed"] else "",
                )
            )
            return None
        cmd = [
            "npx",
            "playwright",
            "test",
            "--config",
            "tests/nhcx/playwright.config.ts",
        ]
        if opts["headed"]:
            cmd.append("--headed")
        env = {"NHCX_TEST_ONLY": tests}
        import os

        return subprocess.call(cmd, cwd=fe, env={**os.environ, **env})  # noqa: S603

    # ---- the payer driver for the GUI runner ----

    def do_payer(self, opts):
        from care.nhcx.services import common
        from care.nhcx.tests.e2e.payer import driver

        claim = common.get_claim(opts["claim"])
        act, rest, stage = opts["act"], opts["rest"], opts["stage"]
        if act == "read":
            out = driver.read(claim, stage)
        elif act == "decide":
            out = driver.decide(claim, stage, rest[0], opts["remarks"])
        elif act == "lines":
            # each arg "status:amount" (e.g. approved:60000 partially_approved:100), "-" skips
            decisions = []
            for a in rest:
                if a in ("-", ""):
                    decisions.append(None)
                    continue
                status, _, amount = a.partition(":")
                decisions.append((status, float(amount) if amount else None))
            out = driver.irdai_lines(claim, stage, decisions)
        elif act == "pay":
            out = driver.irdai_pay(claim, float(rest[0]), rest[1], stage=stage)
        else:
            out = driver.irdai_case(claim, stage)
        self.stdout.write(json.dumps(out, default=str))

    def do_seed_plan(self, opts):
        from care.nhcx.services import common
        from care.nhcx.tests.e2e import seed

        ok, detail = seed.apply(common.get_claim(opts["claim"]))
        self.stdout.write(json.dumps({"seeded": ok, "detail": detail}))

    def do_free_beneficiary(self, opts):
        from care.nhcx.tests.e2e.scenarios.common import free_beneficiary_report

        self.stdout.write(json.dumps(free_beneficiary_report(cfg.load()), default=str))

    def do_report_merge(self, opts):
        conf = cfg.load()
        entries = json.loads(Path(opts["file"]).read_text())
        if isinstance(entries, dict):
            entries = [entries]
        data = report.merge(conf.report_path, conf.report_view(), None, entries)
        self.stdout.write(json.dumps(data["summary"]))

    def do_gui_info(self, opts):
        """What the screens are driven with: the same test data the CLI uses."""
        from care.emr.models import Patient
        from care.nhcx.tests.e2e.scenarios import common as c
        from care.users.models import User

        conf = cfg.load()
        doctor = User.objects.filter(username=conf.get("NHCX_TEST_DOCTOR")).first()
        out = {
            "facility": conf.get("NHCX_TEST_FACILITY"),
            "user": conf.get("NHCX_TEST_USER"),
            "doctor": doctor.full_name if doctor else "",
            "doctor_type": doctor.user_type if doctor else "",
            "diagnosis": (conf.get("NHCX_TEST_DIAGNOSIS") or c.DIAGNOSIS[0]).split()[0],
            "pmjay_package": c.PMJAY_PACKAGE,
            "unknown_member": c.UNKNOWN_MEMBER,
            "payers": {},
        }
        for payer in ("irdai", "pmjay"):
            member = conf.get(f"NHCX_TEST_{payer.upper()}_MEMBER_ID") or ""
            name = f"NHCX E2E {payer.upper()} Beneficiary"
            patient = Patient.objects.filter(name=name, deleted=False).first()
            out["payers"][payer] = {
                "code": conf.get(f"NHCX_TEST_{payer.upper()}_PAYER") or "",
                "member": member,
                "patient": str(patient.external_id) if patient else "",
            }
        self.stdout.write(json.dumps(out))

    def do_gui_lines(self, opts):
        from care.nhcx.services import common
        from care.nhcx.tests.e2e.scenarios import common as c

        claim = common.get_claim(opts["claim"])
        row = claim.plan
        codes = (
            list(
                row.benefits.exclude(rate__isnull=True)
                .order_by("seq")
                .values_list("code", flat=True)
            )
            if row
            else []
        )
        self.stdout.write(
            json.dumps({"codes": codes[: opts["n"]], "package": c.PMJAY_PACKAGE})
        )

    def do_gui_trail(self, opts):
        """The ids a GUI entry reports, read from the claims the screens made."""
        from django.apps import apps

        from care.nhcx.models import Claim
        from care.nhcx.tests.e2e.cli.runner import ledger_ids

        corr = []
        for claim in Claim.objects.filter(external_id__in=opts["claims"]):
            corr.append(claim.correlation_id)
            for model in apps.get_app_config("nhcx").get_models():
                names = {f.name for f in model._meta.fields}  # noqa: SLF001
                keys = sorted(n for n in names if n.endswith("correlation_id"))
                if "claim" not in names or not keys:
                    continue
                for row in model.objects.filter(claim=claim).values_list(*keys):
                    corr += list(row)
        corr = list(dict.fromkeys(str(c) for c in corr if c))
        ledger = []
        for c in corr:
            ledger += [i for i in ledger_ids(c) if i not in ledger]
        self.stdout.write(json.dumps({"correlation_ids": corr, "ledger_ids": ledger}))


def _runners(mode):
    return ("cli", "gui") if mode == "both" else (mode,)


def _blocked(tid, runner, cause, detail, result="blocked"):
    return {
        "id": tid,
        "runner": runner,
        "claim": "",
        "correlation_ids": [],
        "ledger_ids": [],
        "decisions": [],
        "steps": [],
        "result": result,
        "cause": cause,
        "detail": detail,
        "attempts": 0,
    }


def _remove_seeds(entries):
    from care.nhcx.models import Claim
    from care.nhcx.tests.e2e import seed

    ids = [
        c.strip()
        for e in entries
        for c in (e.get("claim") or "").split(",")
        if c.strip()
    ]
    if ids:
        seed.remove(Claim.objects.filter(external_id__in=ids))


def _exit_for(entries):
    """T2L: 1 when a test failed, 2 when one was blocked by setup, else 0."""
    if any(e.get("result") == "fail" for e in entries):
        sys.exit(1)
    if any(e.get("result") == "blocked" and e.get("cause") == "setup" for e in entries):
        sys.exit(2)
