import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class EffortTransitionTests(unittest.TestCase):
    def test_completing_task_reduces_remaining_effort(self):
        script = Path(__file__).resolve().parents[1] / "src/tasks.py"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.json"
            for status, expected in (("todo", 12), ("doing", 12), ("done", 5)):
                with self.subTest(status=status):
                    path.write_text(json.dumps([
                        {"id": "active", "status": status, "points": 7},
                        {"id": "queued", "status": "todo", "points": 5},
                        {"id": "shipped", "status": "done", "points": 19},
                    ]), encoding="utf-8")
                    result = subprocess.run(
                        [sys.executable, str(script), str(path)],
                        cwd=directory, capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
                    report = json.loads(result.stdout)
                    self.assertEqual(report["remaining_points"], expected)
                    self.assertEqual(report["total"], 3)
                    self.assertEqual(report["counts"], {
                        "todo": 1 + (status == "todo"),
                        "doing": int(status == "doing"),
                        "done": 1 + (status == "done"),
                    })
