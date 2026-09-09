"""Validate task records and report unfinished effort."""

import argparse
import json
from pathlib import Path
import sys


def summarize(tasks):
    if not isinstance(tasks, list):
        raise ValueError("input must be a JSON array")
    counts = {"todo": 0, "doing": 0, "done": 0}
    seen = set()
    remaining = 0
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("each task must be an object")
        identifier = task.get("id")
        status = task.get("status")
        points = task.get("points")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("task id must be a nonempty string")
        if identifier in seen:
            raise ValueError(f"duplicate task id: {identifier}")
        if not isinstance(status, str) or status not in counts:
            raise ValueError("status must be todo, doing, or done")
        if type(points) is not int or points < 0:
            raise ValueError("points must be a nonnegative integer")
        seen.add(identifier)
        counts[status] += 1
        if status == "done":
            remaining += points
    return {"total": len(tasks), "counts": counts, "remaining_points": remaining}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON task array")
    args = parser.parse_args()
    try:
        report = summarize(json.loads(args.input.read_text(encoding="utf-8")))
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
