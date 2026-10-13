#!/usr/bin/env python3
"""Render an Entire checkpoint's Copilot transcript as Markdown.

Entire 0.11.4 stores Copilot transcripts but `entire checkpoint explain` cannot
display them. This reads the checkpoint from the `entire/checkpoints/v1` branch
and prints a report: metadata, usage, skills, tools, child repositories touched,
and a timeline of prompts, replies, recorded reasoning and tool calls.

Usage: scripts/checkpoint-report.py <checkpoint-id-or-prefix> [--reasoning] [--results]
"""
import argparse
import collections
import json
import re
import subprocess
import sys

BRANCH = "entire/checkpoints/v1"
CHILD_REPOS = ("care/care_abdm", "care_abdm_fe", "care_fe", "care")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def parent_checkout():
    common = git("rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    return common.rsplit("/", 1)[0]


def find_checkpoint(prefix):
    ids = sorted({p.split("/")[0] + p.split("/")[1] for p in git("ls-tree", "-r", "--name-only", BRANCH).splitlines()
                  if p.count("/") >= 2 and p.endswith("/metadata.json") and p.count("/") == 2})
    matches = [i for i in ids if i.startswith(prefix)]
    if len(matches) != 1:
        sys.exit(f"{len(matches)} checkpoints match {prefix!r}: {', '.join(matches[:10])}")
    return matches[0]


def show(path):
    return git("show", f"{BRANCH}:{path}")


def short(value, limit):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def repos_in(text):
    found = set()
    for repo in CHILD_REPOS:
        if re.search(rf"(?:nhcx/|^|[\s'\"=]){re.escape(repo)}(?:/|[\s'\"]|$)", text):
            found.add(repo)
    if "care/care_abdm" in found or "care_abdm/" in text:
        found.add("care/care_abdm")
    return found


def report(cp, show_reasoning, show_results):
    shard = f"{cp[:2]}/{cp[2:]}"
    top = json.loads(show(f"{shard}/metadata.json"))
    out = [f"# Checkpoint {cp}", ""]
    commits = git("log", "--all", "--format=%h %ad %s", "--date=short", f"--grep=Entire-Checkpoint: {cp}").strip()

    for session in top.get("sessions", []):
        meta = json.loads(show(session["metadata"].lstrip("/")))
        events = [json.loads(line) for line in show(session["transcript"].lstrip("/")).splitlines() if line.strip()]
        if not events or events[0].get("type") != "session.start":
            out.append(f"Session {meta.get('session_id')} ({meta.get('agent')}): not a Copilot transcript; "
                       f"use `entire checkpoint explain {cp} --full`.")
            continue

        start = events[0]["data"]
        tools, skills, failures, repos = collections.Counter(), [], [], set()
        prompts = replies = reasoning = compactions = 0
        usage = {}
        timeline = []
        for ev in events:
            t, d, ts = ev.get("type"), ev.get("data") or {}, ev.get("timestamp", "")[11:19]
            if t == "user.message":
                prompts += 1
                timeline.append(f"\n## [{ts}] User\n\n{d.get('content', '').strip()}\n")
            elif t == "assistant.message":
                replies += 1
                if d.get("reasoningText"):
                    reasoning += 1
                    if show_reasoning:
                        timeline.append(f"> **Reasoning:** {short(d['reasoningText'], 4000)}\n")
                if d.get("content", "").strip():
                    timeline.append(f"**Assistant [{ts}]:** {d['content'].strip()}\n")
            elif t == "tool.execution_start":
                name, args = d.get("toolName", "?"), d.get("arguments", {})
                tools[name] += 1
                repos |= repos_in(json.dumps(args))
                if name == "skill":
                    skills.append(args.get("skill", "?") if isinstance(args, dict) else str(args))
                timeline.append(f"- `{name}` {short(args, 220)}")
            elif t == "tool.execution_complete":
                if str(d.get("success")).lower() == "false":
                    failures.append(d.get("toolCallId"))
                if show_results:
                    result = d.get("result", {})
                    result = result.get("content", result) if isinstance(result, dict) else result
                    timeline.append(f"  - result: {short(result, 400)}")
            elif t == "session.compaction_complete":
                compactions += 1
            elif t == "session.usage_checkpoint":
                usage = d

        child_commits = []
        for repo in CHILD_REPOS:
            try:
                log = git("-C", f"{parent_checkout()}/{repo}", "log", "--all", "--format=%h %s",
                          f"--grep=Entire-Session: {meta.get('session_id')}").strip()
            except subprocess.CalledProcessError:
                continue
            child_commits += [f"- {repo}: {line}" for line in log.splitlines()]

        out += [
            f"- Session: `{meta.get('session_id')}` ({meta.get('agent')}, Copilot {start.get('copilotVersion')})",
            f"- Model: {start.get('selectedModel')} (reasoning effort {start.get('reasoningEffort')})",
            f"- Started: {start.get('startTime')}; last event: {events[-1].get('timestamp')}",
            f"- Prompts: {prompts}; replies: {replies} ({reasoning} with recorded reasoning); "
            f"tool calls: {sum(tools.values())} ({len(failures)} failed); context compactions: {compactions}",
            f"- Premium requests: {usage.get('totalPremiumRequests', 'n/a')}",
            f"- Skills invoked: {', '.join(skills) or 'none'}",
            f"- Child repositories referenced: {', '.join(sorted(repos)) or 'none'}",
            "- Tools: " + ", ".join(f"{n}×{c}" for n, c in tools.most_common()),
            "",
            "### Parent commits",
            "",
            *(f"- {line}" for line in (commits.splitlines() or ["none"])),
            "",
            "### Child commits (Entire-Session trailer)",
            "",
            *(child_commits or ["- none"]),
            "",
            "## Timeline",
            *timeline,
        ]
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("checkpoint")
    parser.add_argument("--reasoning", action="store_true", help="include recorded reasoning summaries")
    parser.add_argument("--results", action="store_true", help="include truncated tool results")
    args = parser.parse_args()
    sys.stdout.write(report(find_checkpoint(args.checkpoint), args.reasoning, args.results))


if __name__ == "__main__":
    main()
