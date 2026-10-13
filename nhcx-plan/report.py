#!/usr/bin/env python3
"""Build nhcx-plan/report.html from the plan files (standard library only).

Run: python3 nhcx-plan/report.py   (or make-report.sh once)
"""

import datetime as dt
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
FILES = {
    "knowledge": "knowledge.json",
    "progress": "progress.json",
    "discovery": "discovery.json",
    "mapping": "mapping.json",
    "plan": "plan.json",
    "code-plan": "code-plan.json",
    "code": "code.json",
    "validation": "validation.json",
    "dry-run": "dry-run.json",
    "e2e": "e2e.json",
}
TABS = [
    ("overview", "Overview"),
    ("progress", "Progress"),
    ("discovery", "Discovery"),
    ("mapping", "Mapping"),
    ("plan", "Plan"),
    ("code-plan", "Code plan"),
    ("code", "Code"),
    ("validation", "Validation"),
    ("dry-run", "Dry-run"),
    ("e2e", "E2E"),
    ("log", "Log"),
]
RESULT_CLASS = {
    "pass": "pass", "passed": "pass", "done": "pass", "found": "pass", "mapped": "pass",
    "written": "pass", "fixed": "pass", "fail": "fail", "failed": "fail", "missing": "fail",
    "error": "fail", "blocked": "blocked", "partial": "blocked", "conflict": "blocked",
    "skip": "skipped", "skipped": "skipped", "new": "skipped",
}


def esc(v):
    return html.escape("" if v is None else str(v))


def load(name):
    path = HERE / FILES[name]
    if not path.exists():
        return None, "not yet written"
    try:
        return json.loads(path.read_text()), None
    except Exception as exc:  # noqa: BLE001
        return None, f"does not parse: {exc}"


def cell(v):
    if isinstance(v, (dict, list)):
        if isinstance(v, list) and all(isinstance(x, str) for x in v):
            return esc(", ".join(v))
        return f"<pre>{esc(json.dumps(v, indent=1, ensure_ascii=False))}</pre>"
    cls = RESULT_CLASS.get(str(v)) if isinstance(v, str) else None
    return f'<span class="{cls}">{esc(v)}</span>' if cls else esc(v)


def table(rows, cols=None):
    if not rows:
        return "<p>(none)</p>"
    if not all(isinstance(r, dict) for r in rows):
        return f"<pre>{esc(json.dumps(rows, indent=1, ensure_ascii=False))}</pre>"
    if cols is None:
        cols = []
        for r in rows:
            for k in r:
                if k not in cols:
                    cols.append(k)
    head = "".join(f"<th>{esc(c)}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{cell(r.get(c, ''))}</td>" for c in cols) + "</tr>" for r in rows)
    return f"<table><tr>{head}</tr>{body}</table>"


def generic(data):
    out = []
    for key, val in data.items():
        out.append(f"<h3>{esc(key)}</h3>")
        if isinstance(val, list):
            out.append(table(val))
        elif isinstance(val, dict) and val and all(isinstance(v, dict) for v in val.values()):
            out.append(table([{"key": k, **v} for k, v in val.items()]))
        else:
            out.append(f"<pre>{esc(json.dumps(val, indent=1, ensure_ascii=False))}</pre>")
    return "".join(out)


def section(name, data, err):
    if err:
        return f"<p class=\"{'fail' if 'parse' in err else 'skipped'}\">{esc(FILES[name])}: {esc(err)}</p>"
    return generic(data)


def collect_errors(docs):
    errors = []
    progress = docs["progress"][0] or {}
    entries = progress.get("entries", [])
    closed = {}
    for e in entries:
        key = (e.get("substep"), e.get("item"))
        if e.get("action") == "blocked":
            closed[key] = e
        elif e.get("action") in ("done", "skipped") and key in closed:
            closed.pop(key)
    for e in reversed(list(closed.values())):
        errors.append(f"{e['id']} {e.get('substep')} blocked: {e.get('item')} — {e.get('blocked_reason') or e.get('summary')}")
    val = docs["validation"][0] or {}
    for f in val.get("files", []):
        if f.get("status") == "failed":
            for c in f.get("checks", []):
                if c.get("result") == "fail" and not c.get("fixed"):
                    errors.append(f"validation {f['path']} {c.get('spec')}: {c.get('finding')}")
    dry = docs["dry-run"][0] or {}
    for t in dry.get("tests", []):
        if t.get("result") == "fail":
            errors.append(f"dry-run {t.get('file')}::{t.get('name')}: {t.get('failure')}")
    e2e = docs["e2e"][0] or {}
    for c in e2e.get("setup", []) if isinstance(e2e.get("setup"), list) else []:
        if c.get("result") in ("fail", "failed"):
            errors.append(f"setup {c.get('check')}: {c.get('detail')}")
    for t in e2e.get("tests", []):
        if t.get("result") in ("fail", "blocked"):
            errors.append(
                f"e2e {t.get('test')} {t.get('runner')} {t.get('result')}: {t.get('detail') or t.get('reason') or ''} "
                f"correlation {t.get('correlation_ids', '')} ledger {t.get('ledger_ids', '')}"
            )
    for name, (_, err) in docs.items():
        if err and "parse" in err:
            errors.append(f"{FILES[name]} {err}")
    return errors


def build():
    docs = {name: load(name) for name in FILES}
    progress = docs["progress"][0] or {}
    target = progress.get("target", {})
    status = progress.get("status", {})
    steps_done = sum(1 for s in status.values() if s.get("state") == "done")
    dry = docs["dry-run"][0] or {}
    summ = dry.get("summary", {})
    run = summ.get("pass", 0) + summ.get("fail", 0)
    errors = collect_errors(docs)
    built = dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

    parts = [
        "<!doctype html><meta charset=\"utf-8\"><title>NHCX integration report</title>",
        "<style>body{font:14px system-ui;margin:2em;max-width:100em}"
        "nav button{margin:0 .3em .3em 0;padding:.3em .8em}nav button.on{font-weight:bold;text-decoration:underline}"
        "section{display:none}section.on{display:block}table{border-collapse:collapse;margin-bottom:1em}"
        "td,th{border:1px solid #ccc;padding:.3em .6em;text-align:left;vertical-align:top}pre{margin:0;white-space:pre-wrap}"
        ".pass{color:#080}.fail{color:#b00}.blocked{color:#b60}.skipped{color:#666}</style>",
        "<h1>NHCX integration report <button onclick=\"location.reload()\">Refresh</button></h1>",
        f"<p>{esc(target.get('repo', ''))} &middot; {esc(target.get('skill', ''))} {esc(target.get('skill_version', ''))}"
        f" &middot; built {built} &middot; {steps_done} of 8 steps done &middot; {summ.get('pass', 0)} of {run} tests passing"
        f" &middot; {len(errors)} open errors</p><nav>",
    ]
    parts += [f'<button data-tab="{t}">{esc(label)}</button>' for t, label in TABS]
    parts.append("</nav>")

    ov = ["<h2>Errors</h2>"]
    ov.append("<ul>" + "".join(f'<li class="fail">{esc(e)}</li>' for e in errors) + "</ul>" if errors else "<p class=\"pass\">No open errors</p>")
    ov.append("<h2>Plan files</h2>")
    ov.append(table([{"file": FILES[n], "state": err or "present"} for n, (_, err) in docs.items()]))
    kn = docs["knowledge"][0]
    if kn:
        ov.append("<h2>Knowledge source</h2>" + generic(kn))
    parts.append(f'<section id="overview">{"".join(ov)}</section>')

    pr = []
    if docs["progress"][1]:
        pr.append(section("progress", None, docs["progress"][1]))
    else:
        rows = []
        for step, st in status.items():
            subs = st.get("substeps", {})
            rows.append({"step": step, "state": st.get("state"),
                         "sub-steps": f"{sum(1 for v in subs.values() if v in ('done', 'blocked', 'skipped'))} / {len(subs)}",
                         "exit checked": "yes" if st.get("exit_checked") else "no"})
        pr.append(table(rows))
        for step, st in status.items():
            if st.get("substeps"):
                pr.append(f"<h3>{esc(step)}</h3><ul>" + "".join(
                    f"<li>[{'x' if v in ('done', 'blocked', 'skipped') else ' '}] {esc(k)} {cell(v)}</li>"
                    for k, v in st["substeps"].items()) + "</ul>")
    parts.append(f'<section id="progress">{"".join(pr)}</section>')

    for name in ("discovery", "mapping", "plan", "code-plan", "code"):
        data, err = docs[name]
        parts.append(f'<section id="{name}">{section(name, data, err)}</section>')

    data, err = docs["validation"]
    if data and isinstance(data.get("files"), list):
        data = dict(data)
        data["files"] = sorted(data["files"], key=lambda f: {"failed": 0, "fixed": 1}.get(f.get("status"), 2))
    parts.append(f'<section id="validation">{section("validation", data, err)}</section>')

    data, err = docs["dry-run"]
    if data and isinstance(data.get("tests"), list):
        data = dict(data)
        data["tests"] = sorted(data["tests"], key=lambda t: {"fail": 0, "skip": 1}.get(t.get("result"), 2))
    parts.append(f'<section id="dry-run">{section("dry-run", data, err)}</section>')
    data, err = docs["e2e"]
    parts.append(f'<section id="e2e">{section("e2e", data, err)}</section>')

    entries = list(reversed(progress.get("entries", [])))
    log_rows = [{"id": e["id"], "time": e["time"], "sub-step": e.get("substep") or e.get("step"), "action": e.get("action"),
                 "item": e.get("item"), "summary": e.get("summary"),
                 "files": [f"{f['path']} {f.get('change', '')} {f.get('lines', '')}" for f in e.get("files", [])]
                 + e.get("plan_files", [])} for e in entries]
    parts.append(f'<section id="log">{table(log_rows)}</section>')
    parts.append(
        "<script>const show=id=>{document.querySelectorAll('section').forEach(s=>s.classList.toggle('on',s.id===id));"
        "document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('on',b.dataset.tab===id));location.hash=id};"
        "document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>show(b.dataset.tab));"
        "show(location.hash.slice(1)||'overview');</script>"
    )
    (HERE / "report.html").write_text("\n".join(parts))


if __name__ == "__main__":
    build()
