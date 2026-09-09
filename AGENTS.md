# merge-gym application contract

## Scope

Maintain the task validator and reporting CLI in `src/tasks.py`. The README
defines its public input and output contract. Keep the application dependency-free.

`telemetry/` and `.github/workflows/observe.yml` / `report.yml` are controller-owned
observability infrastructure. Application fixes do not modify them. Observers run
only trusted pinned code and publish allowed public metadata. Reports publish an
external controller result; they do not evaluate scenario correctness.

## Changes

Add a failing behavior test before changing behavior. Preserve CLI exit codes,
JSON output, validation rules, and usability from an unrelated working directory.
Do not weaken tests or workflow checks to make a change pass.

## Verification

Run `python3 -m unittest discover -s tests -v` from the repository root. Include
subprocess coverage for CLI changes. Keep `application-tests` as the stable CI
job name.

Telemetry CLI changes require real subprocess tests. Keep observer/report outputs
under `RUNNER_TEMP`, outside the checkout. Do not add review-event observers or
attach telemetry checks to fixture PR heads. Never publish raw event files,
transcripts, credentials, review bodies, or hidden expected results.

PR and review observations belong to the external controller. GitHub Actions
observers use only filtered workflow_run events: pull_request_target creates
a check on the fixture HEAD and therefore changes the tested check set.
