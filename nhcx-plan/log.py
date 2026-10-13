#!/usr/bin/env python3
"""Append an entry to nhcx-plan/progress.json and regenerate progress.md.

Usage (standard library only):
  python3 nhcx-plan/log.py --step L5 --substep L5.2 --action done \
      --item care/nhcx/gateway/send.py --summary "G7 send" \
      --file "care/nhcx/gateway/send.py:created:1-120:G7 send" \
      --plan-file nhcx-plan/code.json --spec G7 --spec G9
  python3 nhcx-plan/log.py --init "<repo>" "<skill>" "<version>"
  python3 nhcx-plan/log.py --substeps L1 L1.0,L1.1,...   (declare a step's sub-steps)
"""

import argparse
import datetime as dt
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROGRESS = HERE / "progress.json"
MD = HERE / "progress.md"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

STEP_TITLES = {
    "L1": "Discovery",
    "L2": "Mapping",
    "L3": "Integration Planning",
    "L4": "Code Planning",
    "L5": "Write Code",
    "L6": "Validate Code",
    "L7": "Dry-run Tests",
    "L8": "End-to-end Tests",
}
CLOSING = {"done", "blocked", "skipped"}


def now():
    return dt.datetime.now(IST).isoformat(timespec="seconds")


def load():
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text())
    return {"target": {}, "declared": {}, "status": {}, "entries": []}


def recompute(data):
    status = {}
    declared = data.get("declared", {})
    for step in STEP_TITLES:
        subs = {s: "not_started" for s in declared.get(step, [])}
        exit_checked = False
        for e in data["entries"]:
            if e["step"] != step:
                continue
            if e["action"] == "exit_checked":
                exit_checked = True
                continue
            sub = e.get("substep") or step
            if sub == step:
                continue
            if e["action"] == "started" and subs.get(sub) not in CLOSING:
                subs[sub] = "in_progress"
            elif e["action"] in CLOSING:
                subs[sub] = e["action"]
        if not subs and not exit_checked:
            state = "not_started"
        elif any(v == "blocked" for v in subs.values()):
            state = "blocked"
        elif exit_checked and all(v in CLOSING for v in subs.values()):
            state = "done"
        else:
            state = "in_progress"
        status[step] = {"state": state, "exit_checked": exit_checked, "substeps": subs}
    data["status"] = status


def render_md(data):
    out = ["# NHCX integration progress", "", "## Status", ""]
    out += ["| Step | State | Sub-steps done | Exit checked |", "|---|---|---|---|"]
    for step, title in STEP_TITLES.items():
        st = data["status"].get(step, {"state": "not_started", "substeps": {}})
        subs = st["substeps"]
        done = sum(1 for v in subs.values() if v in CLOSING)
        out.append(
            f"| {step} {title} | {st['state'].replace('_', ' ')} | {done} / {len(subs)} | "
            f"{'yes' if st.get('exit_checked') else 'no'} |"
        )
    for step, title in STEP_TITLES.items():
        subs = data["status"].get(step, {}).get("substeps", {})
        if not subs:
            continue
        out += ["", f"## {step} {title}"]
        for sub, state in subs.items():
            mark = "x" if state in CLOSING else " "
            extra = "" if state in ("done", "not_started") else f" ({state.replace('_', ' ')})"
            out.append(f"- [{mark}] {sub}{extra}")
    out += ["", "## Changes", "", "| Id | Time | Sub-step | Action | Summary | Files |", "|---|---|---|---|---|---|"]
    for e in data["entries"]:
        files = "; ".join(
            f"`{f['path']}` {f.get('change', '')} {f.get('lines', '')}".strip() for f in e.get("files", [])
        )
        plans = "; ".join(f"`{p}`" for p in e.get("plan_files", []))
        cell = "; ".join(x for x in (files, plans) if x)
        summary = e.get("summary", "").replace("|", "\\|").replace("\n", " ")
        out.append(
            f"| {e['id']} | {e['time'][:16].replace('T', ' ')} | {e.get('substep') or e['step']} | "
            f"{e['action']} | {summary} | {cell} |"
        )
    MD.write_text("\n".join(out) + "\n")


def save(data):
    recompute(data)
    PROGRESS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    render_md(data)


def parse_file(spec):
    parts = spec.split(":", 3)
    parts += [""] * (4 - len(parts))
    return {"path": parts[0], "change": parts[1] or "modified", "lines": parts[2], "why": parts[3]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--init", nargs=3, metavar=("REPO", "SKILL", "VERSION"))
    p.add_argument("--substeps", nargs=2, metavar=("STEP", "LIST"))
    p.add_argument("--step")
    p.add_argument("--substep", default="")
    p.add_argument("--action")
    p.add_argument("--item", default="")
    p.add_argument("--summary", default="")
    p.add_argument("--file", action="append", default=[], help="path:change:lines:why")
    p.add_argument("--plan-file", action="append", default=[])
    p.add_argument("--spec", action="append", default=[])
    p.add_argument("--commit", default="")
    p.add_argument("--corrects", default="")
    p.add_argument("--blocked-reason", default="")
    a = p.parse_args()
    data = load()
    if a.init:
        data["target"] = {"repo": a.init[0], "started_at": now(), "skill": a.init[1], "skill_version": a.init[2]}
    if a.substeps:
        data.setdefault("declared", {})[a.substeps[0]] = [s for s in a.substeps[1].split(",") if s]
    if a.action:
        n = len(data["entries"]) + 1
        entry = {
            "id": f"LOG-{n:04d}",
            "time": now(),
            "step": a.step,
            "substep": a.substep,
            "action": a.action,
            "item": a.item,
            "summary": a.summary,
            "files": [parse_file(f) for f in a.file],
            "plan_files": a.plan_file,
            "specs": a.spec,
            "commit": a.commit,
            "corrects": a.corrects,
            "blocked_reason": a.blocked_reason,
        }
        data["entries"].append(entry)
        print(entry["id"])
    save(data)


if __name__ == "__main__":
    main()
