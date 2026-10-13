"""Run with python3 -m unittest discover -s scripts -p 'test_*.py'."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import checkpoint_transcripts as transcripts

spec = importlib.util.spec_from_file_location('report', Path(__file__).with_name('checkpoint-report.py'))
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class TranscriptTests(unittest.TestCase):
    def render(self, events, **flags):
        opts = SimpleNamespace(reasoning=False, results=False, system=False, raw_events=False)
        for k, v in flags.items():
            setattr(opts, k, v)
        with patch.object(report, 'child_commits', return_value=[]):
            return '\n'.join(report.render(events, {}, '', opts))

    def test_codex_no_mirror_duplicates_and_cumulative_usage(self):
        events = [
            {'type': 'session_meta', 'payload': {'id': 'test'}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'hello'}]}},
            {'type': 'event_msg', 'payload': {'type': 'user_message', 'message': 'hello'}},
            {'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'shell', 'arguments': '{}'}},
            {'type': 'response_item', 'payload': {'type': 'custom_tool_call', 'name': 'patch', 'input': 'change'}},
            {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'total_token_usage': {'input_tokens': 10}}}},
            {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'total_token_usage': {'input_tokens': 25}}}},
        ]
        output = self.render(events)
        self.assertEqual(output.count('hello'), 1)
        self.assertIn('shell×1, patch×1', output)
        self.assertIn('"input_tokens": 25', output)
        self.assertIn('user prompts: 1', output)

    def test_codex_visibility_flags(self):
        events = [
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'developer', 'content': 'instructions-secret'}},
            {'type': 'response_item', 'payload': {'type': 'reasoning', 'summary': [{'text': 'summary-secret'}], 'encrypted_content': 'cipher-secret'}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'channel': 'analysis', 'content': 'analysis-secret'}},
            {'type': 'response_item', 'payload': {'type': 'function_call_output', 'output': 'result-secret'}},
        ]
        self.assertNotIn('-secret', self.render(events))
        output = self.render(events, reasoning=True, results=True, system=True)
        for value in ('instructions-secret', 'summary-secret', 'result-secret', 'analysis-secret'):
            self.assertIn(value, output)
        self.assertNotIn('cipher-secret', output)

    def test_claude_blocks_and_tool_only_user(self):
        events = [
            {'type': 'assistant', 'sessionId': 'claude', 'message': {'role': 'assistant', 'model': 'claude', 'content': [
                {'type': 'text', 'text': 'answer'}, {'type': 'tool_use', 'name': 'Read', 'input': {'file': 'a'}},
                {'type': 'thinking', 'thinking': 'private-summary'}]}},
            {'type': 'user', 'message': {'role': 'user', 'content': [{'type': 'tool_result', 'is_error': True, 'content': 'missing file'}]}},
        ]
        output = self.render(events)
        self.assertIn('Read×1', output)
        self.assertIn('user prompts: 0', output)
        self.assertIn('FAILED: missing file', output)
        self.assertNotIn('private-summary', output)

    def test_opencode_json_export(self):
        events = transcripts.load_events(json.dumps({'info': {'id': 'session'}, 'messages': [
            {'info': {'role': 'assistant', 'modelID': 'model', 'sessionID': 'session'}, 'parts': [
                {'type': 'text', 'text': 'hello export'},
                {'type': 'tool', 'tool': 'read', 'state': {'input': {'path': 'a'}, 'output': 'file text'}}]}]}))
        output = self.render(events, results=True)
        self.assertIn('hello export', output)
        self.assertIn('read×1', output)
        self.assertIn('file text', output)

    def test_copilot_regression(self):
        events = [{'type': 'session.start', 'data': {'sessionId': 'copilot'}},
                  {'type': 'user.message', 'data': {'content': 'prompt'}},
                  {'type': 'assistant.message', 'data': {'content': 'answer', 'model': 'model'}},
                  {'type': 'tool.execution_start', 'data': {'toolName': 'bash'}}]
        output = self.render(events)
        self.assertIn('Copilot', output)
        self.assertIn('User prompts: 1; replies: 1', output)
        self.assertIn('bash×1', output)

    def test_unknown_format_is_visible(self):
        events = [{'type': 'new-format', 'payload': {'text': 'original'}}]
        self.assertIn('without a dedicated parser: new-format×1', self.render(events))
        self.assertIn('original', self.render(events, raw_events=True))

    def test_partial_live_tail_only(self):
        with patch('sys.stderr'):
            self.assertEqual(transcripts.load_events('{"type":"a"}\n{"type":', live=True), [{'type': 'a'}])
        for text in ('{"type":"a"}\n{"type":', '{broken}\n{"type":"a"}\n'):
            with self.assertRaises(ValueError):
                transcripts.load_events(text)
        with self.assertRaises(ValueError):
            transcripts.load_events('{broken}\n', live=True)

    def test_entire_api_accepts_any_agent(self):
        results = [SimpleNamespace(returncode=0, stdout='{"agent":"Factory AI Droid"}', stderr=''),
                   SimpleNamespace(returncode=0, stdout='{"role":"user","content":"hello"}', stderr='')]
        with patch.object(transcripts.subprocess, 'run', side_effect=results):
            events, meta, source = transcripts.resolve_session('session')
        self.assertEqual(meta['agent'], 'Factory AI Droid')
        self.assertEqual(events[0]['content'], 'hello')
        self.assertIn('Entire', source)

    def test_unregistered_codex_fallback_and_ambiguity(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ', {'CODEX_HOME': tmp}), \
                patch.object(transcripts.Path, 'home', return_value=Path(tmp)), \
                patch.object(transcripts.subprocess, 'run', side_effect=FileNotFoundError('entire')):
            folder = Path(tmp) / 'sessions/2026/10/13'
            folder.mkdir(parents=True)
            (folder / 'rollout-date-example.jsonl').write_text('{"type":"session_meta","payload":{"id":"example"}}\n')
            events, meta, source = transcripts.resolve_session('example')
            self.assertEqual(meta['agent'], 'Codex')
            self.assertIn('native agent storage', meta['capture_note'])
            (folder / 'rollout-other-example.jsonl').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Multiple transcripts'):
                transcripts.resolve_session('example')
            with self.assertRaisesRegex(ValueError, 'No live transcript'):
                transcripts.resolve_session('missing')

    def test_invalid_id_and_json(self):
        for sid in ('../secret', '*', ''):
            with self.assertRaises(ValueError):
                transcripts.resolve_session(sid)
        for text in ('42', '[1, 2]', '{"messages":"wrong"}'):
            with self.assertRaises(ValueError):
                transcripts.load_events(text)

    def test_cli_missing_file_has_no_traceback(self):
        result = subprocess.run(['python3', str(Path(report.__file__)), '--transcript', '/nonexistent/transcript.jsonl'],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checkpoint-report:', result.stderr)
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
