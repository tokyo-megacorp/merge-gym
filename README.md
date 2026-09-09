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

Task reports are deterministic for the same input.
