"""Controller-owned deterministic transient CI failure; no application changes."""

import os
import sys


def transient_failure(head_ref, run_attempt):
    prefix = "gym-run/flake-"
    if not head_ref.startswith(prefix) or len(head_ref) == len(prefix):
        return False
    attempt = int(run_attempt)
    if attempt < 1:
        raise ValueError("workflow attempt must be positive")
    return attempt == 1


def main():
    try:
        fail = transient_failure(os.environ.get("GYM_HEAD_REF", ""), os.environ.get("GYM_RUN_ATTEMPT", ""))
    except ValueError:
        print("merge-gym: invalid workflow attempt metadata", file=sys.stderr)
        return 2
    if fail:
        print("merge-gym: transient service unavailable (controlled fixture); rerun the workflow without changing source", file=sys.stderr)
        return 75
    return 0


if __name__ == "__main__":
    sys.exit(main())
