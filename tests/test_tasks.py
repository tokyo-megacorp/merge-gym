import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.tasks import summarize


class SummaryTests(unittest.TestCase):
    def test_counts_tasks_and_remaining_effort(self):
        tasks = [
            {"id": "a", "status": "todo", "points": 3},
            {"id": "b", "status": "doing", "points": 2},
            {"id": "c", "status": "done", "points": 8},
        ]
        self.assertEqual(summarize(tasks), {
            "total": 3, "counts": {"todo": 1, "doing": 1, "done": 1},
            "remaining_points": 5,
        })

    def test_empty_input(self):
        self.assertEqual(summarize([])["remaining_points"], 0)

    def test_rejects_invalid_records(self):
        invalid = [
            {}, {"id": "", "status": "todo", "points": 1},
            {"id": "a", "status": "blocked", "points": 1},
            {"id": "a", "status": "todo", "points": -1},
            {"id": "a", "status": "todo", "points": True},
            {"id": "a", "status": "todo", "points": 1.5},
            {"id": "a", "status": ["todo"], "points": 1},
            None,
        ]
        for record in invalid:
            with self.subTest(record=record), self.assertRaises(ValueError):
                summarize([record])

    def test_rejects_duplicate_ids(self):
        task = {"id": "same", "status": "todo", "points": 0}
        with self.assertRaises(ValueError):
            summarize([task, task])

    def test_rejects_non_list_input(self):
        with self.assertRaises(ValueError):
            summarize({})


class CliTests(unittest.TestCase):
    def invoke(self, content):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.json"
            path.write_text(content)
            return subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parents[1] / "src/tasks.py"), str(path)],
                cwd=directory, capture_output=True, text=True,
            )

    def test_cli_from_unrelated_directory(self):
        result = self.invoke('[{"id":"a","status":"todo","points":4}]')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["remaining_points"], 4)
        self.assertEqual(result.stderr, "")

    def test_cli_reopening_completed_task_restores_remaining_effort(self):
        for status, expected in (("done", 4), ("todo", 13), ("doing", 13)):
            with self.subTest(status=status):
                result = self.invoke(json.dumps([
                    {"id": "reopened", "status": status, "points": 9},
                    {"id": "queued", "status": "todo", "points": 4},
                    {"id": "shipped", "status": "done", "points": 20},
                ]))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(json.loads(result.stdout)["remaining_points"], expected)

    def test_cli_completed_tasks_have_no_remaining_effort(self):
        result = self.invoke('[{"id":"shipped","status":"done","points":8}]')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "total": 1, "counts": {"todo": 0, "doing": 0, "done": 1},
            "remaining_points": 0,
        })
        self.assertEqual(result.stderr, "")

    def test_cli_mixed_statuses_count_only_unfinished_points(self):
        result = self.invoke(json.dumps([
            {"id": "planned", "status": "todo", "points": 3},
            {"id": "active", "status": "doing", "points": 7},
            {"id": "shipped", "status": "done", "points": 12},
            {"id": "unestimated", "status": "todo", "points": 0},
        ]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "total": 4, "counts": {"todo": 2, "doing": 1, "done": 1},
            "remaining_points": 10,
        })
        self.assertEqual(result.stderr, "")

    def test_cli_mixed_statuses_sum_only_unfinished_effort(self):
        result = self.invoke(json.dumps([
            {"id": "planned", "status": "todo", "points": 3},
            {"id": "active", "status": "doing", "points": 7},
            {"id": "shipped", "status": "done", "points": 20},
        ]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "total": 3, "counts": {"todo": 1, "doing": 1, "done": 1},
            "remaining_points": 10,
        })
        self.assertEqual(result.stderr, "")

    def test_cli_in_progress_tasks_contribute_remaining_effort(self):
        result = self.invoke('[{"id":"active","status":"doing","points":7}]')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "total": 1, "counts": {"todo": 0, "doing": 1, "done": 0},
            "remaining_points": 7,
        })
        self.assertEqual(result.stderr, "")

    def test_cli_reports_input_errors_without_partial_output(self):
        for content in ("{", '[{"id":"a"}]'):
            with self.subTest(content=content):
                result = self.invoke(content)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn("error:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_cli_mixed_statuses_sum_only_unfinished_points(self):
        result = self.invoke(json.dumps([
            {"id": "planned", "status": "todo", "points": 3},
            {"id": "active", "status": "doing", "points": 7},
            {"id": "shipped", "status": "done", "points": 20},
            {"id": "zero", "status": "todo", "points": 0},
        ]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), {
            "total": 4, "counts": {"todo": 2, "doing": 1, "done": 1},
            "remaining_points": 10,
        })


if __name__ == "__main__":
    unittest.main()
