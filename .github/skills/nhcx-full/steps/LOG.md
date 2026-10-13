# Progress Log

Every step and sub-step leaves a record of what it did and which files it changed. The record is `nhcx-plan/progress.json`; `nhcx-plan/progress.md` is the same record for people to read, regenerated from the JSON after every entry and never edited by hand. `nhcx-plan/report.html` is the one page a person opens to see where the work stands: progress, test results and errors, rebuilt at the end of every prompt.

#### LOGW. WHEN TO WRITE
- When a sub-step starts (`started`) and when it ends (`done`, `blocked` or `skipped`).
- Every time a file is created, modified or deleted, in the target source or under `nhcx-plan/`, as part of that sub-step.
- When an earlier step's plan file is corrected (`corrected`), naming the file and what was wrong.
- When a step finishes and its exit condition is checked.

Entries are appended, never rewritten. A mistake in an entry is fixed by a new `corrected` entry that points at the old one.

#### LOGJ. progress.json

```json
{
  "target": {"repo": "", "started_at": "<ISO time>", "skill": "", "skill_version": ""},
  "status": {
    "L5": {
      "state": "not_started | in_progress | done | blocked",
      "exit_checked": false,
      "substeps": {"L5.1": "done", "L5.2": "in_progress"}
    }
  },
  "entries": [
    {
      "id": "LOG-0042",
      "time": "<ISO time>",
      "step": "L5",
      "substep": "L5.2",
      "action": "started | done | blocked | skipped | corrected | exit_checked",
      "item": "the file, spec id or exchange the sub-step is working on",
      "summary": "what was done, in one or two sentences",
      "files": [
        {"path": "", "change": "created | modified | deleted", "lines": "", "why": ""}
      ],
      "plan_files": ["nhcx-plan/code.json"],
      "specs": ["A4", "F8", "D18"],
      "commit": "",
      "corrects": "",
      "blocked_reason": ""
    }
  ]
}
```

- `id` counts up from `LOG-0001` and is never reused.
- `files` lists target source files; `plan_files` lists the `nhcx-plan/` files touched. An entry with neither changed nothing and says so in `summary`.
- `lines` is the changed range after the change.
- `commit` is filled when the change is committed (L5.5 commits per batch).
- `status` is recomputed from `entries` after each append.

#### LOGM. progress.md

Regenerated from progress.json:

```markdown
# NHCX integration progress

## Status
| Step | State | Sub-steps done | Exit checked |
|---|---|---|---|
| L1 Discovery | done | 8 / 8 | yes |
| L5 Write Code | in progress | 3 / 5 | no |

## L5 Write Code
- [x] L5.1 Take the next file
- [ ] L5.2 Write it (in progress: `src/claims/preauth.py`)

## Changes
| Id | Time | Sub-step | Action | Summary | Files |
|---|---|---|---|---|---|
| LOG-0042 | 2026-09-22 10:14 | L5.2 | done | Pre-auth send service (A4) | `src/claims/preauth.py` created 1-188; `nhcx-plan/code.json` |
```

One section per step, in step order, with a checkbox per sub-step; the changes table lists every entry, newest last.

#### LOGH. report.html

Rebuilt as the last action of every prompt, however the prompt ended: after a step, part of a step, a fix, a test run, or a question answered without any change. It is written from the plan files only, never from memory of the conversation, so it says what the records say. It is never edited by hand.

**Built by a script, not by hand.** The page is produced by a report builder the skill writes into the target at L1, in the target's own language and kept beside the plan files: `nhcx-plan/report.py` for a Python target, `nhcx-plan/report.mjs` for Node, `nhcx-plan/report.php` for PHP, `nhcx-plan/Report.java` (or a Gradle/Maven task) for Java, and so on, with no dependency beyond the language's standard library. It reads `nhcx-plan/*.json` and writes `nhcx-plan/report.html`. Rebuilding the report means running that script; the agent runs it at the end of every prompt, and a person can run it at any time.

**Wrapper scripts, one per platform.** Beside it, `nhcx-plan/make-report.sh` (POSIX shell, executable) and `nhcx-plan/make-report.bat` (Windows), both doing the same thing: run the report builder, wait 10 seconds, run it again, and keep doing so until stopped (Ctrl-C). One line of output per rebuild, with the time. So a person opens `report.html` once, leaves `make-report.sh` running, and the page is at most 10 seconds behind the plan files; its refresh button (below) shows the latest build. Both scripts resolve the builder relative to their own location, so they work from any working directory, and they exit with the builder's status when a single run is asked for (`make-report.sh once`).

**Reads:** every file under `nhcx-plan/`: `progress.json`, `knowledge.json`, `discovery.json`, `mapping.json`, `plan.json`, `code-plan.json`, `code.json`, `validation.json`, `dry-run.json`, `e2e.json`, and `progress.md`. A file that does not exist yet is shown as "not yet written", never as a pass. A file that does not parse is shown with its parse error, and the rest of the page still builds.

**One page, tabs.** Everything is on one page, one tab per source, with the Overview first:

| Tab | Shows |
|---|---|
| Overview | The target repository, the skill and its version, when the page was built, and one line of overall state: steps done out of 8, tests passing out of run, open errors. Then **Errors**: everything open, newest first: `blocked` entries and their reasons, failed validation items, failed dry-run tests, failed or blocked end-to-end tests with their detail, correlation ids and ledger ids, and failed setup checks. An error that a later entry resolves is left out. "No open errors" when there are none. |
| Progress | One row per step, L1 to L8: state, sub-steps done out of total, exit checked; then the sub-step checklist of every step, as `progress.md` shows it. |
| Discovery | `discovery.json`: the knowledge source, the target's technology, and every spec item as found, partial or missing, with its file and lines. |
| Mapping | `mapping.json`: target fields against database columns and FHIR elements. |
| Plan | `plan.json`: phases, steps and sub-steps, with their status. |
| Code plan | `code-plan.json`: files, functions and order. |
| Code | `code.json`: every file written, its specs and status. |
| Validation | `validation.json`: each file against its specs, failures first. |
| Dry-run | `dry-run.json`: pass, fail and skip counts, then every test with its result and failure text. |
| E2E | `e2e.json`: setup checks, then one row per test and runner (GUI, CLI) with result, cause and attempts; blocked tests with their reason. |
| Log | Every `progress.json` entry, newest first: time, sub-step, action, item, summary, files. |

Each tab renders its file's records as tables, with the fields that file's spec names as columns. Any structure the builder does not know is still shown, as pretty-printed JSON, so nothing in a plan file is invisible. Long text is not cut short.

**Minimal, self-contained HTML.** One file that opens from disk in any browser and needs nothing else: no external stylesheets, fonts, images or scripts, no framework. Plain semantic tags (`h1`, `h2`, `table`, `ul`, `pre`) with a few lines of inline CSS for the tab bar, table borders and a colour for the result words (pass, fail, blocked, skipped). A few lines of inline script, and no more: the tab bar shows one tab's section and hides the others (the current tab kept in the URL hash, so a reload stays on it), and a **Refresh** button at the top reloads the page (`location.reload()`), which shows whatever the last rebuild wrote. Without script the page still reads top to bottom, every section visible. No secrets: configuration values are shown as `set` or `missing`, as [T1. Test Configuration](../tests/T1-test-configuration.md) does.

```html
<!doctype html>
<meta charset="utf-8">
<title>NHCX integration report</title>
<style>
body{font:14px system-ui;margin:2em;max-width:80em}
nav button{margin:0 .3em .3em 0;padding:.3em .8em}nav button.on{font-weight:bold;text-decoration:underline}
section{display:none}section.on{display:block}
table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:.3em .6em;text-align:left;vertical-align:top}
.pass{color:#080}.fail{color:#b00}.blocked{color:#b60}.skipped{color:#666}
</style>
<h1>NHCX integration report <button onclick="location.reload()">Refresh</button></h1>
<p>acme-hmis &middot; nhcx-full 1.2.0 &middot; built 2026-09-30 10:14:05 &middot; 5 of 8 steps done &middot; 31 of 34 tests passing &middot; 2 open errors</p>
<nav>
<button data-tab="overview">Overview</button><button data-tab="progress">Progress</button><button data-tab="discovery">Discovery</button>
<button data-tab="mapping">Mapping</button><button data-tab="plan">Plan</button><button data-tab="code-plan">Code plan</button>
<button data-tab="code">Code</button><button data-tab="validation">Validation</button><button data-tab="dry-run">Dry-run</button>
<button data-tab="e2e">E2E</button><button data-tab="log">Log</button>
</nav>
<section id="overview"><h2>Errors</h2><ul><li>T14 cli: no pre-auth decision within 120 s; correlation 5b1f0c1e, ledger 7UQ2P0AB</li></ul></section>
<section id="progress"><table><tr><th>Step</th><th>State</th><th>Sub-steps</th><th>Exit checked</th></tr>
<tr><td>L5 Write Code</td><td>in progress</td><td>3 / 5</td><td>no</td></tr></table></section>
<section id="e2e"><table><tr><th>Test</th><th>Runner</th><th>Result</th><th>Cause</th><th>Attempts</th></tr>
<tr><td>T14</td><td>cli</td><td class="fail">fail</td><td>ours</td><td>2</td></tr></table></section>
<section id="log"><table><tr><th>Time</th><th>Sub-step</th><th>Action</th><th>Summary</th></tr></table></section>
<script>
const show=id=>{document.querySelectorAll('section').forEach(s=>s.classList.toggle('on',s.id===id));
document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('on',b.dataset.tab===id));location.hash=id};
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>show(b.dataset.tab));
show(location.hash.slice(1)||'overview');
</script>
```

```sh
#!/bin/sh
# nhcx-plan/make-report.sh: rebuild report.html every 10 seconds until stopped.
# "make-report.sh once" rebuilds it one time and exits with the builder's status.
cd "$(dirname "$0")" || exit 1
build() { python3 report.py; }          # the target's builder: node report.mjs, php report.php, ...
if [ "$1" = once ]; then build; exit $?; fi
while :; do
  build && echo "$(date '+%H:%M:%S') report.html rebuilt" || echo "$(date '+%H:%M:%S') report build failed"
  sleep 10
done
```

```bat
@echo off
rem nhcx-plan\make-report.bat: rebuild report.html every 10 seconds until stopped (Ctrl-C).
rem "make-report.bat once" rebuilds it one time.
cd /d "%~dp0"
if "%1"=="once" ( python report.py & exit /b %errorlevel% )
:loop
python report.py && echo %time% report.html rebuilt || echo %time% report build failed
timeout /t 10 /nobreak >nul
goto loop
```

The builder and the two wrapper scripts are written in L1 (before any other plan file, so every later step can rebuild the page) and logged like any other file. The build of the page is itself logged: one entry, action `done`, item `nhcx-plan/report.html`, in the sub-step that was running (or the last one, when the prompt ran none).

#### LOGX. EXIT
- Every sub-step of a finished step has a `started` and a closing entry.
- Every file named in code.json, and every file changed in the target, appears in at least one entry's `files`.
- progress.md matches progress.json.
- report.html was rebuilt at the end of the last prompt by the report builder, and its counts match the plan files.
- `nhcx-plan/make-report.sh once` and `make-report.bat once` rebuild it and exit 0.
