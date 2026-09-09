"""Publish a sanitized external controller result; do not infer a verdict."""

import argparse
import json
import math
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from telemetry.public_fields import choice, exact_keys, integer, text
from telemetry.report_signature import verified_dispatch

STATUSES = ("pass", "behavior_failure", "infrastructure_inconclusive", "unexercised")
IDENTIFIER = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}"


def _scenario(value):
    exact_keys(value, ("id", "status", "prs"))
    identifier = text(value["id"], IDENTIFIER)
    status = choice(value["status"], STATUSES)
    if not isinstance(value["prs"], list):
        raise ValueError("invalid PR list")
    links = [f"[#{integer(pr)}](https://github.com/tokyo-megacorp/merge-gym/pull/{pr})" for pr in value["prs"]]
    return f"| {identifier} | {status} | {', '.join(links) or '—'} |"


def render(value):
    exact_keys(value, ("run_id", "status", "duration_seconds", "scenarios"))
    run_id, status = text(value["run_id"], IDENTIFIER), choice(value["status"], STATUSES)
    duration = value["duration_seconds"]
    if type(duration) not in (int, float) or not math.isfinite(duration) or duration < 0:
        raise ValueError("invalid duration")
    if not isinstance(value["scenarios"], list) or not value["scenarios"]:
        raise ValueError("missing scenario results")
    rows = [_scenario(scenario) for scenario in value["scenarios"]]
    return (f"# Merge-gym · {run_id}\n\nExternal controller result: **{status}**\n\n"
            f"Duration: {duration:g} seconds.\n\nThis workflow publishes the supplied result; "
            "it does not verify scenarios. Detailed evidence remains with the controller.\n\n"
            "| Scenario | External result | PRs |\n| --- | --- | --- |\n" + "\n".join(rows) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", type=Path)
    parser.add_argument("--dispatch-event", action="store_true")
    args = parser.parse_args()
    try:
        value = json.loads(args.input_file.read_text())
        if args.dispatch_event:
            value = json.loads(verified_dispatch(value))
        output = render(value)
    except (OSError, ValueError, TypeError):
        print("telemetry: invalid sanitized report", file=sys.stderr)
        return 2
    print(output, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
