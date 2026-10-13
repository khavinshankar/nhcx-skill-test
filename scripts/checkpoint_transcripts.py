"""Agent-independent transcript discovery and non-Copilot report adapters.

Entire owns provider-specific storage for registered sessions. Native discovery
is a fallback for sessions whose capture hooks have not run. No transcript is
uploaded or registered by this module.
"""
import collections
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def load_events(text, live=False):
    """Accept JSON documents or JSONL; only live, unterminated tails may be partial."""
    if not text.strip():
        return []
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        rows = text.splitlines(keepends=True)
        values = []
        for i, row in enumerate(rows):
            if not row.strip():
                continue
            try:
                values.append(json.loads(row))
            except json.JSONDecodeError as exc:
                if live and i == len(rows) - 1 and not row.endswith('\n'):
                    print('Warning: ignored an incomplete live transcript tail.', file=sys.stderr)
                    break
                raise ValueError(f'Invalid JSON on transcript line {i + 1}: {exc.msg}') from exc
        value = values
    if isinstance(value, dict):
        # OpenCode exports and generic JSON message/event envelopes.
        value = value.get('messages', value.get('events', [value]))
    if not isinstance(value, list) or any(not isinstance(e, dict) for e in value):
        raise ValueError('Expected transcript objects in JSONL or a JSON events/messages array.')
    return value


def read_snapshot(path):
    with open(path, 'rb') as stream:
        return stream.read(os.fstat(stream.fileno()).st_size).decode('utf-8')


def resolve_session(sid):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', sid):
        raise ValueError('Session IDs may contain only letters, digits, underscores and hyphens.')
    meta, diagnostic = {'session_id': sid}, ''
    try:
        result = subprocess.run(['entire', 'session', 'info', sid, '--json'],
                                capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            try:
                info = json.loads(result.stdout)
                if isinstance(info, dict):
                    meta.update(info)
            except json.JSONDecodeError:
                pass
        result = subprocess.run(['entire', 'session', 'info', sid, '--transcript'],
                                capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            return load_events(result.stdout, live=True), meta, 'Entire live transcript API'
        diagnostic = (result.stderr or result.stdout).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        diagnostic = str(exc)

    home = Path.home()
    codex = Path(os.environ.get('CODEX_HOME', home / '.codex'))
    claude = Path(os.environ.get('CLAUDE_CONFIG_DIR', home / '.claude'))
    candidates = [(home / '.copilot/session-state' / sid / 'events.jsonl', 'Copilot CLI')]
    for root, pattern, agent in (
        (codex / 'sessions', f'**/*-{sid}.jsonl', 'Codex'),
        (codex / 'archived_sessions', f'**/*-{sid}.jsonl', 'Codex'),
        (claude / 'projects', f'*/{sid}.jsonl', 'Claude Code'),
        (home / '.cursor/projects', f'*/agent-transcripts/{sid}.jsonl', 'Cursor'),
        (home / '.cursor/projects', f'*/agent-transcripts/{sid}/{sid}.jsonl', 'Cursor'),
        (home / '.factory/sessions', f'**/{sid}.jsonl', 'Factory AI Droid'),
    ):
        candidates.extend((p, agent) for p in root.glob(pattern))
    matches = {p.resolve(): agent for p, agent in candidates if p.is_file()}
    if len(matches) > 1:
        raise ValueError('Multiple transcripts match; choose one with --transcript:\n' +
                         '\n'.join(str(p) for p in matches))
    if not matches:
        raise ValueError(f'No live transcript found for session {sid}. '
                         'Use --transcript PATH for an exported JSON/JSONL transcript, '
                         'or a checkpoint ID for an archived Entire checkpoint. '
                         f'Entire diagnostic: {diagnostic or "unavailable"}')
    path, agent = next(iter(matches.items()))
    meta['agent'] = agent
    meta['capture_note'] = ('Read from native agent storage; this does not establish '
                            'that Entire has checkpointed the session.')
    return load_events(read_snapshot(path), live=True), meta, str(path)


def text_content(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return '\n'.join(text_content(v) for v in value if isinstance(v, (str, dict)))
    if isinstance(value, dict):
        for key in ('text', 'content', 'thinking'):
            if key in value:
                return text_content(value[key])
    return ''


def agent_format(events, meta):
    if any(e.get('type') == 'session.start' for e in events):
        return 'Copilot CLI'
    if any(e.get('type') in ('session_meta', 'response_item', 'turn_context') for e in events):
        return 'Codex'
    return meta.get('agent') or 'Generic JSON'


def render_generic(events, meta, commits, opts, short, child_commits):
    """Render Codex responses, Claude-style blocks, OpenCode exports and generic records."""
    agent = agent_format(events, meta)
    sid = meta.get('session_id')
    models, tools, kinds = collections.Counter(), collections.Counter(), collections.Counter()
    timeline, unknown = [], collections.Counter()
    prompts = replies = 0
    usage = None

    def message(role, content):
        nonlocal prompts, replies
        if role == 'user':
            prompts += 1
        elif role == 'assistant':
            replies += 1
        if role in ('system', 'developer') and not opts.system:
            return
        if content:
            timeline.append(f'\n### {role.title()}\n\n{content}\n')

    def blocks(content):
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
            t = block.get('type')
            if t in ('tool_use', 'tool_call', 'tool'):
                name = block.get('name') or block.get('tool') or '?'
                state = block.get('state') or {}
                tools[name] += 1
                timeline.append(f"- `{name}` {short(block.get('input', state.get('input', {})), 220)}")
                if state.get('error'):
                    timeline.append(f"  - FAILED: {short(state['error'], 400)}")
                elif opts.results and 'output' in state:
                    timeline.append(f"  - result: {short(state['output'], 400)}")
            elif t == 'tool_result':
                if block.get('is_error') or opts.results:
                    label = 'FAILED' if block.get('is_error') else 'result'
                    timeline.append(f"- {label}: {short(block.get('content', ''), 400)}")
            elif t in ('thinking', 'reasoning') and opts.reasoning:
                timeline.append(f"> Recorded reasoning: {short(text_content(block), 4000)}")

    for ev in events:
        t = ev.get('type', 'message')
        kinds[t] += 1
        p = ev.get('payload') or {}
        if t == 'session_meta':
            sid = sid or p.get('id') or p.get('session_id')
            if opts.system:
                message('system', text_content(p.get('base_instructions')))
        elif t == 'turn_context':
            if p.get('model'):
                models[p['model']] += 1
        elif t == 'response_item':
            rt = p.get('type')
            if rt == 'message':
                # Analysis-channel text is subject to the same opt-in as reasoning blocks.
                if p.get('channel') != 'analysis' or opts.reasoning:
                    message(p.get('role', 'assistant'), text_content(p.get('content')))
            elif rt in ('function_call', 'custom_tool_call'):
                name = p.get('name', '?')
                tools[name] += 1
                timeline.append(f"- `{name}` {short(p.get('arguments', p.get('input', '')), 220)}")
            elif rt in ('function_call_output', 'custom_tool_call_output'):
                if opts.results:
                    timeline.append(f"  - result [{p.get('call_id', '?')}]: {short(p.get('output', ''), 400)}")
            elif rt == 'reasoning':
                if opts.reasoning:
                    timeline.append(f"> Recorded reasoning summary: {short(text_content(p.get('summary')), 4000)}")
            else:
                unknown[f'response_item/{rt}'] += 1
        elif t == 'event_msg':
            # Codex mirrors messages/tool activity here; count canonical response_items only.
            if p.get('type') == 'token_count':
                usage = (p.get('info') or {}).get('total_token_usage') or usage
            elif p.get('type') in ('error', 'warning'):
                timeline.append(f"- {p['type']}: {short(p, 400)}")
        elif t == 'token_usage_record':
            usage = p.get('thread_token_usage') or usage
        elif isinstance(ev.get('message'), dict) or ev.get('role') or isinstance(ev.get('info'), dict):
            msg = ev.get('message') if isinstance(ev.get('message'), dict) else ev.get('info', ev)
            sid = sid or ev.get('sessionId') or msg.get('sessionID')
            role = msg.get('role', t)
            content = ev.get('parts', msg.get('content', ''))
            visible = [b for b in content if isinstance(b, str) or
                       (isinstance(b, dict) and b.get('type') in ('text', 'input_text', 'output_text'))] if isinstance(content, list) else content
            # A tool-result-only user record is not a new user prompt.
            if text_content(visible):
                message(role, text_content(visible))
            blocks(content)
            model = msg.get('model') or msg.get('modelID')
            if isinstance(model, str):
                models[model] += 1
            if msg.get('usage'):
                timeline.append(f"- Message usage (not session total): {short(msg['usage'], 500)}")
        elif t == 'system':
            if opts.system:
                timeline.append(f"- System event: {short(ev, 2000)}")
        else:
            unknown[t] += 1

    out = [f"- Session: `{sid or 'unknown'}` ({agent})",
           f"- Events: {len(events)}; user prompts: {prompts}; assistant messages: {replies}",
           f"- Models observed: {', '.join(models) or meta.get('model') or 'not recorded'}",
           '- Tools: ' + (', '.join(f'{n}×{c}' for n, c in tools.most_common()) or 'none parsed'),
           f"- Latest recorded cumulative token usage: {json.dumps(usage) if usage else 'not available'}",
           '- Event types: ' + ', '.join(f'{n}×{c}' for n, c in kinds.items())]
    if meta.get('capture_note'):
        out.append('- ' + meta['capture_note'])
    if unknown:
        out.append('- Events without a dedicated parser: ' + ', '.join(f'{n}×{c}' for n, c in unknown.items()) +
                   '. Use --raw-events to inspect the original records.')
    out += ['', '### Parent commits', '', *[f'- {c}' for c in commits.splitlines() or ['none']],
            '', '### Child commits (Entire-Session trailer)', '',
            *((child_commits(sid) if sid else []) or ['- none']), '', '## Timeline', *timeline]
    if opts.raw_events:
        out += ['', '## Raw events (includes recorded instructions, reasoning and results)', '',
                '```json', json.dumps(events, ensure_ascii=False, indent=2), '```']
    return out
