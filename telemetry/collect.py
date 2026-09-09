"""Project GitHub event metadata onto a public allowlist; never collect bodies."""

import argparse
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from telemetry.public_fields import choice, integer, object_value, text, timestamp

REPOSITORY = "tokyo-megacorp/merge-gym"
PR_ACTIONS = ("opened", "reopened", "closed", "synchronize", "edited", "ready_for_review", "converted_to_draft")
CONCLUSIONS = (None, "success", "failure", "neutral", "cancelled", "skipped", "timed_out", "action_required", "stale", "startup_failure")


def _ref(value):
    value = object_value(value)
    return {"sha": text(value.get("sha"), r"[0-9a-f]{40}"),
            "ref": text(value.get("ref"), r"[A-Za-z0-9_./-]{1,256}")}


def _pr(value):
    value = object_value(value)
    head, base = _ref(value.get("head")), _ref(value.get("base"))
    return {"id": integer(value.get("id")), "number": integer(value.get("number")),
            "state": choice(value.get("state"), ("open", "closed")),
            "head_sha": head["sha"], "head_ref": head["ref"], "base_sha": base["sha"], "base_ref": base["ref"],
            "created_at": timestamp(value.get("created_at")), "updated_at": timestamp(value.get("updated_at"))}


def _workflow(value):
    value = object_value(value)
    choice(value.get("name"), ("Scenario CI",))
    prs = value.get("pull_requests", [])
    if not isinstance(prs, list):
        raise ValueError("invalid workflow PR list")
    return {"id": integer(value.get("id")), "name": "Scenario CI", "run_attempt": integer(value.get("run_attempt")),
            "head_sha": text(value.get("head_sha"), r"[0-9a-f]{40}"),
            "head_branch": text(value.get("head_branch"), r"[A-Za-z0-9_./-]{1,256}"),
            "status": choice(value.get("status"), ("queued", "in_progress", "completed", "requested", "waiting", "pending")),
            "conclusion": choice(value.get("conclusion"), CONCLUSIONS),
            "prs": [integer(object_value(pr).get("number")) for pr in prs],
            "created_at": timestamp(value.get("created_at")), "updated_at": timestamp(value.get("updated_at"))}


def collect(event_name, payload):
    payload = object_value(payload)
    choice(event_name, ("pull_request_target", "workflow_run"))
    choice(object_value(payload.get("repository")).get("full_name"), (REPOSITORY,))
    actor = text(object_value(payload.get("sender")).get("login"), r"[A-Za-z0-9_-]{1,100}(?:\[bot\])?")
    result = {"schema_version": 1, "repository": REPOSITORY, "event_name": event_name, "actor": actor}
    if event_name == "pull_request_target":
        result.update(action=choice(payload.get("action"), PR_ACTIONS), pull_request=_pr(payload.get("pull_request")))
    else:
        result.update(action=choice(payload.get("action"), ("requested", "in_progress", "completed")),
                      workflow_run=_workflow(payload.get("workflow_run")))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event_file", type=Path)
    parser.add_argument("--event-name", required=True)
    args = parser.parse_args()
    try:
        output = collect(args.event_name, json.loads(args.event_file.read_text()))
    except (OSError, ValueError, TypeError):
        print("telemetry: invalid or unsupported event metadata", file=sys.stderr)
        return 2
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
