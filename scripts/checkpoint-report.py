#!/usr/bin/env python3
"""Render agent transcripts stored by Entire or native agents as Markdown.

Originally a Copilot workaround: Entire 0.11.4 stores raw events.jsonl up to the
commit) but `entire checkpoint explain` cannot display them, and its metadata
leaves the model, token usage and touched files empty. This reads the
transcript and reports metadata, usage, models, skills, MCP servers, subagents,
errors, child repositories touched, and a timeline of prompts, replies,
recorded reasoning and tool calls. Subagent activity is labelled and is not
counted as user prompts.

Sources:
  <checkpoint-id-or-prefix>   from entire/checkpoints/v1 (or --ref <commit>)
  --session <id>              Entire's live transcript API, then native log discovery
  --transcript <path>         a JSON/JSONL transcript or export from any agent

Usage: scripts/checkpoint-report.py (<checkpoint> | --session ID | --transcript PATH)
                                    [--reasoning] [--results] [--system] [--raw-events]
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys
from checkpoint_transcripts import (agent_format, load_events, read_snapshot,
                                    render_generic, resolve_session)

BRANCH = "entire/checkpoints/v1"
CHILD_REPOS = ("care/care_abdm", "care_abdm_fe", "care_fe", "care")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def parent_checkout():
    common = git("rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    return common.rsplit("/", 1)[0]


def find_checkpoint(prefix, ref):
    ids = sorted({p.split("/")[0] + p.split("/")[1] for p in git("ls-tree", "-r", "--name-only", ref).splitlines()
                  if p.endswith("/metadata.json") and p.count("/") == 2})
    matches = [i for i in ids if i.startswith(prefix)]
    if not matches:
        try:
            trailer = git("log", "-1", "--format=%(trailers:key=Entire-Checkpoint,valueonly)", prefix, "--").strip()
        except subprocess.CalledProcessError:
            trailer = ""
        matches = [i for i in ids if trailer and i == trailer.splitlines()[0]]
    if len(matches) != 1:
        sys.exit(f"{len(matches)} checkpoints match {prefix!r}: {', '.join(matches[:10])}")
    return matches[0]


def partial_usage(usage, events, subagents):
    """Token data Copilot logs before session.shutdown; Entire records none of it."""
    parts = []
    if usage.get("totalNanoAiu") is not None:
        parts.append(f"{usage['totalNanoAiu'] / 1e9:,.1f} AI units billed")
    for state in usage.get("promptCacheBreakState") or []:
        if state.get("conversation") == "main":
            for model, m in (state.get("models") or {}).items():
                parts.append(f"last {model} prompt {m.get('prompt_tokens')} tokens "
                             f"({m.get('tool_tokens')} tool definitions)")
    sub = sum(s.get("tokens") or 0 for s in subagents.values())
    if sub:
        parts.append(f"subagents {sub} tokens")
    for ev in events:
        if ev.get("type") == "session.compaction_complete":
            used = (ev.get("data") or {}).get("compactionTokensUsed") or {}
            parts.append(f"compaction {used.get('inputTokens')} in/{used.get('outputTokens')} out")
    return "; ".join(parts) or "n/a"


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


def child_commits(session_id):
    lines = []
    for repo in CHILD_REPOS:
        try:
            log = git("-C", f"{parent_checkout()}/{repo}", "log", "--all", "--format=%h %s",
                      "--fixed-strings", f"--grep=Entire-Session: {session_id}").strip()
        except subprocess.CalledProcessError:
            continue
        lines += [f"- {repo}: {line}" for line in log.splitlines()]
    return lines


def render(events, meta, commits, opts):
    if agent_format(events, meta) != 'Copilot CLI':
        return render_generic(events, meta, commits, opts, short, child_commits)
    start = next((e.get('data') or {} for e in events if e.get('type') == 'session.start'), {})
    session_id = meta.get("session_id") or start.get("sessionId")
    types = collections.Counter(e.get("type") for e in events)
    tools, mcp, models, skills = (collections.Counter() for _ in range(4))
    failures, errors, repos, model_changes = [], [], set(), []
    subagents, asks = {}, {}
    prompts = replies = reasoning = 0
    system_chars = 0
    usage, shutdown = {}, {}
    timeline = []

    for ev in events:
        t, d, ts = ev.get("type"), ev.get("data") or {}, ev.get("timestamp", "")[11:19]
        agent = ev.get("agentId")
        sub = subagents.setdefault(agent, {}) if agent else None
        who = f"[subagent {sub.get('name', agent[:8])}] " if agent else ""
        if t == "user.message":
            if agent:
                timeline.append(f"\n### [{ts}] {who}prompt\n\n{short(d.get('content', ''), 2000)}\n")
            else:
                prompts += 1
                timeline.append(f"\n## [{ts}] User\n\n{d.get('content', '').strip()}\n")
        elif t == "system.message":
            if not agent:
                system_chars += len(d.get("content", ""))
            if opts.system and not agent:
                timeline.append(f"\n<details><summary>[{ts}] System / instructions</summary>\n\n"
                                f"{d.get('content', '')}\n\n</details>\n")
        elif t == "assistant.message":
            if not agent:
                replies += 1
            if d.get("model"):
                models[d["model"]] += 1
            if d.get("reasoningText"):
                reasoning += 1
                if opts.reasoning:
                    timeline.append(f"> {who}**Reasoning:** {short(d['reasoningText'], 4000)}\n")
            if d.get("content", "").strip():
                timeline.append(f"**{who}Assistant [{ts}]:** {d['content'].strip()}\n")
        elif t == "tool.execution_start":
            name, args = d.get("toolName", "?"), d.get("arguments", {})
            tools[name] += 1
            if d.get("mcpServerName"):
                mcp[d["mcpServerName"]] += 1
            repos |= repos_in(json.dumps(args))
            if name == "ask_user":
                asks[d.get("toolCallId")] = True
            timeline.append(f"- {who}`{name}` {short(args, 220)}")
        elif t == "tool.execution_complete":
            if str(d.get("success")).lower() == "false":
                failures.append(d.get("toolCallId"))
                timeline.append(f"  - {who}FAILED: {short(d.get('error') or d.get('result'), 300)}")
            elif asks.pop(d.get("toolCallId"), False):
                result = d.get("result", {})
                timeline.append(f"  - {who}**User answered:** "
                                f"{short(result.get('content', result) if isinstance(result, dict) else result, 2000)}")
            elif opts.results:
                result = d.get("result", {})
                result = result.get("content", result) if isinstance(result, dict) else result
                timeline.append(f"  - result: {short(result, 400)}")
        elif t == "skill.invoked":
            skills[d.get("name", "?")] += 1
            timeline.append(f"- {who}skill loaded: `{d.get('name')}` from {d.get('path')} "
                            f"({len(d.get('content', ''))} chars)")
        elif t == "subagent.started":
            sub = sub if sub is not None else subagents.setdefault(d.get('agentId', 'unknown'), {})
            sub.update(name=d.get("agentDisplayName"), type=d.get("agentType"), model=d.get("model"),
                       description=d.get("agentDescription"), status="running")
            timeline.append(f"- {who}started: {d.get('agentType')} — {d.get('agentDescription')}")
        elif t in ("subagent.completed", "subagent.failed"):
            sub = sub if sub is not None else subagents.setdefault(d.get('agentId', 'unknown'), {})
            sub.update(status=t.split(".")[1], tools=d.get("totalToolCalls"), tokens=d.get("totalTokens"),
                       ms=d.get("durationMs"), error=d.get("error"))
            timeline.append(f"- {who}{t.split('.')[1]} ({d.get('totalToolCalls')} tool calls, "
                            f"{d.get('totalTokens')} tokens){': ' + d['error'] if d.get('error') else ''}")
        elif t == "session.model_change" and not agent:
            model_changes.append(f"{ts} → {d.get('newModel')} ({d.get('reasoningEffort')})")
        elif t == "session.error":
            errors.append(f"{ts} {who}{short(d.get('message'), 200)}")
        elif t == "session.usage_checkpoint":
            usage = d
        elif t == "session.shutdown":
            shutdown = d

    tokens = shutdown.get("tokenDetails") or {}
    out = [
        f"- Session: `{session_id}` ({meta.get('agent', 'Copilot CLI')}, Copilot {start.get('copilotVersion')})",
        f"- Model at start: {start.get('selectedModel')} (reasoning effort {start.get('reasoningEffort')}); "
        f"replies by model: {', '.join(f'{m}×{c}' for m, c in models.most_common()) or 'n/a'}",
        f"- Model changes: {'; '.join(model_changes) or 'none'}",
        f"- Started: {start.get('startTime')}; last event: {events[-1].get('timestamp')}; events: {len(events)}",
        f"- User prompts: {prompts}; replies: {replies} ({reasoning} messages with recorded reasoning, "
        f"incl. subagents); tool calls: {sum(tools.values())} ({len(failures)} failed); "
        f"context compactions: {types['session.compaction_complete']}",
        f"- Premium requests: {usage.get('totalPremiumRequests', shutdown.get('totalPremiumRequests', 'n/a'))}"
        + (f"; tokens in/out/cache-read/cache-write: " + "/".join(
            str((tokens.get(k) or {}).get("tokenCount", 0)) for k in ("input", "output", "cache_read", "cache_write"))
           if tokens else " (token totals are only logged at session end)"),
        f"- Usage before session end: {partial_usage(usage, events, subagents)}",
        f"- System prompt and instructions captured: {system_chars} chars (show with --system)",
        f"- Skills loaded: {', '.join(skills) or 'none'}",
        f"- MCP servers: {', '.join(f'{s}×{c}' for s, c in mcp.most_common()) or 'none'}",
        f"- Child repositories referenced: {', '.join(sorted(repos)) or 'none'}",
        "- Tools: " + ", ".join(f"{n}×{c}" for n, c in tools.most_common()),
        "- Event types: " + ", ".join(f"{n}×{c}" for n, c in sorted(types.items())),
        "",
        "### Subagents",
        "",
        *([f"- {s.get('name')} ({s.get('type')}, {s.get('model')}): {s.get('status')}; "
           f"{s.get('tools')} tool calls, {s.get('tokens')} tokens, {s.get('ms')} ms"
           f"{'; ' + s['error'] if s.get('error') else ''}" for s in subagents.values()] or ["- none"]),
        "",
        "### Errors",
        "",
        *([f"- {e}" for e in errors] or ["- none"]),
        "",
        "### Parent commits",
        "",
        *(f"- {line}" for line in (commits.splitlines() or ["none"])),
        "",
        "### Child commits (Entire-Session trailer)",
        "",
        *(child_commits(session_id) or ["- none"]),
        "",
        "## Timeline",
        *timeline,
    ]
    if meta.get('capture_note'):
        out.insert(1, '- ' + meta['capture_note'])
    if opts.raw_events:
        out += ['', '## Raw events', '', '```json', json.dumps(events, ensure_ascii=False, indent=2), '```']
    return out


def load_jsonl(text):
    return load_events(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("checkpoint", nargs="?")
    parser.add_argument("--ref", default=BRANCH, help=f"commit or branch holding checkpoints (default {BRANCH})")
    parser.add_argument("--session", help="read an agent session through Entire or native storage")
    parser.add_argument("--transcript", help="read an agent JSON/JSONL transcript or export")
    parser.add_argument("--raw-events", action="store_true", help="include original events, including instructions, reasoning and results")
    parser.add_argument("--reasoning", action="store_true", help="include recorded reasoning")
    parser.add_argument("--results", action="store_true", help="include truncated tool results")
    parser.add_argument("--system", action="store_true", help="include the system prompt and instructions")
    opts = parser.parse_args()
    if sum(map(bool, (opts.checkpoint, opts.session, opts.transcript))) != 1:
        parser.error("give exactly one of: checkpoint, --session, --transcript")

    if opts.checkpoint:
        cp = find_checkpoint(opts.checkpoint, opts.ref)
        shard = f"{cp[:2]}/{cp[2:]}"
        top = json.loads(git("show", f"{opts.ref}:{shard}/metadata.json"))
        commits = git("log", "--all", "--format=%h %ad %s", "--date=short", f"--grep=Entire-Checkpoint: {cp}").strip()
        out = [f"# Checkpoint {cp}", ""]
        for session in top.get("sessions", []):
            meta = json.loads(git("show", f"{opts.ref}:{session['metadata'].lstrip('/')}"))
            events = load_jsonl(git("show", f"{opts.ref}:{session['transcript'].lstrip('/')}"))
            out += render(events, meta, commits, opts) + [""]
    else:
        if opts.session:
            events, meta, path = resolve_session(opts.session)
        else:
            path = os.path.expanduser(opts.transcript)
            events, meta = load_events(read_snapshot(path)), {}
        sid = meta.get('session_id') or next((
            e.get('sessionId') or (e.get('data') or {}).get('sessionId') or
            ((e.get('payload') or {}).get('id') if e.get('type') == 'session_meta' else None)
            for e in events if e.get('sessionId') or (e.get('data') or {}).get('sessionId') or e.get('type') == 'session_meta'), '')
        meta['session_id'] = sid
        commits = ""
        if sid:
            try:
                commits = git("log", "--all", "--format=%h %ad %s", "--date=short",
                              f"--grep=Entire-Session: {sid}").strip()
            except subprocess.CalledProcessError:
                pass
        out = [f"# Transcript {path}", ""] + render(events, meta, commits, opts)
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        sys.exit(f"checkpoint-report: {detail}")
