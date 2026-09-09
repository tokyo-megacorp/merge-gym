import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from telemetry.collect import collect
from telemetry.render_report import render

ROOT = Path(__file__).resolve().parents[1]


def pr_event():
    return {"repository": {"full_name": "tokyo-megacorp/merge-gym", "secret": "hidden"},
            "sender": {"login": "fixture-bot", "token": "hidden"}, "action": "opened",
            "pull_request": {"id": 90, "number": 7, "state": "open", "draft": False,
                             "head": {"sha": "a" * 40, "ref": "gym/run-1"},
                             "base": {"sha": "b" * 40, "ref": "gym/manual"},
                             "body": "private transcript", "title": "secret title",
                             "created_at": "2026-09-09T10:00:00Z", "updated_at": "2026-09-09T10:01:00Z"}}


def summary():
    return {"run_id": "gym-001", "status": "pass", "duration_seconds": 42,
            "scenarios": [{"id": "happy-path", "status": "pass", "prs": [7]}]}


class CollectorTests(unittest.TestCase):
    def test_pr_projection_drops_all_freeform_content(self):
        result = collect("pull_request_target", pr_event())
        text = json.dumps(result)
        self.assertNotIn("secret", text)
        self.assertNotIn("private transcript", text)
        self.assertNotIn("token", text)
        self.assertEqual(result["pull_request"]["head_sha"], "a" * 40)
        self.assertEqual(result, collect("pull_request_target", pr_event()))

    def test_workflow_projection_filters_source_and_preserves_failed_conclusion(self):
        event = pr_event()
        event["action"] = "completed"
        event["workflow_run"] = {"id": 123, "name": "Scenario CI", "run_attempt": 2,
                                 "head_sha": "a" * 40, "head_branch": "gym/run-1",
                                 "status": "completed", "conclusion": "failure",
                                 "created_at": "2026-09-09T10:00:00Z", "updated_at": "2026-09-09T10:01:00Z",
                                 "pull_requests": [{"number": 7}], "logs": "hidden"}
        result = collect("workflow_run", event)
        self.assertEqual(result["workflow_run"]["conclusion"], "failure")
        self.assertNotIn("logs", json.dumps(result))
        event["workflow_run"]["name"] = "Gym Observe"
        with self.assertRaises(ValueError):
            collect("workflow_run", event)

    def test_missing_identity_and_unsupported_event_fail_closed(self):
        with self.assertRaises(ValueError):
            collect("pull_request_review", pr_event())
        event = pr_event()
        del event["pull_request"]["head"]
        with self.assertRaises(ValueError):
            collect("pull_request_target", event)


class ReportTests(unittest.TestCase):
    def test_publishes_external_result_with_attribution(self):
        result = render(summary())
        self.assertIn("External controller result", result)
        self.assertIn("happy-path", result)
        self.assertIn("https://github.com/tokyo-megacorp/merge-gym/pull/7", result)

    def test_rejects_extra_fields_and_freeform_injection(self):
        for invalid in (dict(summary(), transcript="secret"), dict(summary(), run_id="<script>"),
                        dict(summary(), duration_seconds=float("nan")), dict(summary(), status="success")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                render(invalid)

    def test_scenario_extra_fields_rejected(self):
        value = summary()
        value["scenarios"][0]["oracle"] = "hidden"
        with self.assertRaises(ValueError):
            render(value)


def invoke(script, payload, extra=()):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.json"
        path.write_text(json.dumps(payload))
        return subprocess.run([sys.executable, str(ROOT / "telemetry" / script), str(path), *extra],
                              cwd=directory, capture_output=True, text=True)


class TelemetryCliTests(unittest.TestCase):
    def test_collector_bare_script(self):
        result = invoke("collect.py", pr_event(), ("--event-name", "pull_request_target"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["repository"], "tokyo-megacorp/merge-gym")

    def test_renderer_bare_script(self):
        result = invoke("render_report.py", summary())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("External controller result", result.stdout)

    def test_renderer_rejects_unsigned_dispatch_payload(self):
        payload = {"inputs": {"sanitized_json": json.dumps(summary())}}
        result = invoke("render_report.py", payload, ("--dispatch-event",))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")

    def test_invalid_dispatch_input_fails_without_echo(self):
        payload = {"inputs": {"sanitized_json": '$(echo never-print-this)'}}
        result = invoke("render_report.py", payload, ("--dispatch-event",))
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("never-print-this", result.stderr)

    def test_cli_errors_do_not_echo_rejected_input(self):
        for script, extra in (("render_report.py", ()), ("collect.py", ("--event-name", "workflow_run"))):
            result = invoke(script, {"secret": "never-print-this"}, extra)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("never-print-this", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
