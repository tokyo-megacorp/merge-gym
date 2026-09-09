# merge-gym application contract

## Scope

Maintain the task validator and reporting CLI in `src/tasks.py`. The README
defines its public input and output contract. Keep the application dependency-free.

## Changes

Add a failing behavior test before changing behavior. Preserve CLI exit codes,
JSON output, validation rules, and usability from an unrelated working directory.
Do not weaken tests or workflow checks to make a change pass.

## Verification

Run `python3 -m unittest discover -s tests -v` from the repository root. Include
subprocess coverage for CLI changes. Keep `application-tests` as the stable CI
job name.
