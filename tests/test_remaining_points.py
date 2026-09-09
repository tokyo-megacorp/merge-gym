"""Regression coverage for remaining effort across task completion."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class RemainingPointsTests(unittest.TestCase):
    def test_completing_task_reduces_remaining_effort(self):
        tasks = [
            {"id": "planned", "status": "todo", "points": 3},
            {"id": "active", "status": "doing", "points": 7},
            {"id": "shipped", "status": "done", "points": 12},
        ]
        script = Path(__file__).resolve().parents[1] / "src/tasks.py"
        with tempfile.TemporaryDirectory() as directory:
            task_file = Path(directory) / "tasks.json"
            for status, expected in (("doing", 10), ("done", 3)):
                with self.subTest(status=status):
                    tasks[1]["status"] = status
                    task_file.write_text(json.dumps(tasks), encoding="utf-8")
                    result = subprocess.run(
                        [sys.executable, str(script), str(task_file)],
                        cwd=directory, capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
                    self.assertEqual(json.loads(result.stdout)["remaining_points"], expected)
