# merge-gym

A small Python task-report application used to exercise pull-request maintenance.
It uses only the Python standard library and requires Python 3.11 or newer.

## Run

```sh
python3 src/tasks.py tasks.json
python3 -m unittest discover -s tests -v
```

The input is a JSON array of task objects:

```json
[
  {"id": "write-docs", "status": "todo", "points": 3},
  {"id": "ship", "status": "done", "points": 5}
]
```

Each task needs a unique, nonblank string `id`, a `status` of `todo`, `doing`, or
`done`, and nonnegative integer `points`. Booleans and fractional points are
invalid. IDs are case-sensitive and compared exactly. Extra fields are ignored.

The command prints one JSON report with `total`, counts for each status, and
`remaining_points` (the sum of points for tasks not done). Empty arrays are valid.
Invalid input or unreadable files produce an error on stderr, no report on stdout,
and exit status 2. Successful reports exit with status 0.

GitHub Actions runs the same tests on pushes and pull requests. The check name is
`application-tests`; the workflow can also be started manually.

## Transient CI fixture

For controller-selected branches named `gym-run/flake-<id>`, `application-tests`
fails on workflow attempt 1 with an explicit transient-service diagnostic. Rerun
the same workflow without modifying the source: attempt 2 and later proceed to
the application tests. Other branch names do not activate the fixture.

`ci/transient.py` reads `GYM_HEAD_REF` and `GYM_RUN_ATTEMPT`, supplied from GitHub
Actions metadata as environment values. The workflow uses the PR head branch for
PR runs and the branch ref for push/manual runs. Push and PR workflows have
independent attempt counters; each matching workflow initially fails once.
Passing the probe does not bypass the real application tests.

This infrastructure tests the agent's retry behavior. It must not be edited to
repair an injected transient failure. Runtime retry verification is performed by
the external controller, not by this fixture.

## Public telemetry

`Gym Observe` projects `Scenario CI` workflow events into a small JSON artifact.
PR lifecycle and review observations belong to the external controller. Only repository, actor, PR/ref/SHA, state, CI conclusion, numeric
identifiers and timestamps are permitted. PR titles, bodies, review content and
logs are not collected. Unknown event kinds and malformed fields fail closed.
Repeated identical input produces identical output; workflow run/attempt IDs in
artifact names distinguish observations, not GitHub delivery identities.

`Gym Report` accepts an external controller summary on `main` and publishes a
Markdown step summary and artifact. Dispatch requires `sanitized_json`, the exact
UTF-8 serialization of the summary below, and `signature`, its base64-encoded
RSA-2048/SHA256 signature. The renderer verifies origin with the public key from
its pinned checkout before parsing or rendering. The dedicated private key stays
with the controller, outside the repository and tested agent mounts.

The summary has exactly this shape:

```json
{
  "run_id": "gym-001",
  "status": "pass",
  "duration_seconds": 42,
  "scenarios": [{"id": "happy-path", "status": "pass", "prs": [7]}]
}
```

Statuses are `pass`, `behavior_failure`, `infrastructure_inconclusive`, or
`unexercised`. IDs contain only letters, numbers, `_`, `.`, and `-`. Extra fields
are rejected. The signature authenticates the publisher; it does not verify
scenario correctness. Submit only already sanitized data: workflow dispatch inputs themselves
are not a private storage channel, even if the renderer later rejects them.

Both workflows check out a trusted collector commit, never PR code or artifacts
from the triggering workflow. The observer only follows `Scenario CI`, so report
and observer runs cannot trigger an observer loop. All generated outputs use
`RUNNER_TEMP`; artifacts are convenience copies, not the private evidence archive.

Use only the filtered `workflow_run` trigger for observation. A live probe showed
that `pull_request_target` adds an observer check to the fixture HEAD, changing
the check set consumed by the skill. Verify check isolation after workflow changes.

Observers are asynchronous and incomplete. They cannot prove ordering-sensitive
races or replace decisive review/API observations collected by the external
controller. Review events are intentionally collected externally: a
`pull_request_review` workflow would attach additional checks to the PR context.

Deployment uses two commits: commit changed trusted code, public keys and tests
first; then update the affected workflow's checkout reference to that exact commit
before publishing the workflow commit. Unchanged observers may retain their
existing trusted revision. Never deploy a placeholder. Pin action revisions to
verified upstream commits during that publication step.
