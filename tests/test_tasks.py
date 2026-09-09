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

    def test_cli_completed_tasks_have_no_remaining_effort(self):
        result = self.invoke('[{"id":"shipped","status":"done","points":8}]')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "total": 1, "counts": {"todo": 0, "doing": 0, "done": 1},
            "remaining_points": 0,
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


if __name__ == "__main__":
    unittest.main()
