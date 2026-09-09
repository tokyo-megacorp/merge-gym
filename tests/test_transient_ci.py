import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ci.transient import transient_failure

SCRIPT = Path(__file__).resolve().parents[1] / "ci/transient.py"


class TransientCiTests(unittest.TestCase):
    def test_selected_branch_fails_first_attempt_only(self):
        self.assertTrue(transient_failure("gym-run/flake-example", "1"))
        self.assertFalse(transient_failure("gym-run/flake-example", "2"))
        self.assertFalse(transient_failure("gym-run/flake-example", "3"))

    def test_other_branches_are_unaffected(self):
        for branch in ("main", "gym/manual", "gym-run/happy-1", "feature/flake-one", "gym-run/flake-"):
            self.assertFalse(transient_failure(branch, "1"))

    def test_invalid_selected_attempt_is_not_silently_passed(self):
        for attempt in ("0", "-1", "first", ""):
            with self.subTest(attempt=attempt), self.assertRaises(ValueError):
                transient_failure("gym-run/flake-example", attempt)

    def test_cli_rerun_changes_only_attempt_environment(self):
        env = dict(os.environ, GYM_HEAD_REF="gym-run/flake-example", GYM_RUN_ATTEMPT="1")
        with tempfile.TemporaryDirectory() as directory:
            first = subprocess.run([sys.executable, str(SCRIPT)], cwd=directory, env=env,
                                   capture_output=True, text=True)
            env["GYM_RUN_ATTEMPT"] = "2"
            second = subprocess.run([sys.executable, str(SCRIPT)], cwd=directory, env=env,
                                    capture_output=True, text=True)
        self.assertEqual(first.returncode, 75)
        self.assertIn("transient service unavailable", first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)

    def test_cli_ordinary_branch_is_unaffected(self):
        env = dict(os.environ, GYM_HEAD_REF="main", GYM_RUN_ATTEMPT="1")
        result = subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
