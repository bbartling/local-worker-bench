# Working on this tool

Use synthetic fixtures only. Never commit application credentials, private logs,
model weights, or customer data. Keep generated results under ignored `results/`.

Model calls require an explicit user request for the current task. Use four
threads by default, one local worker at a time, and unload afterward. Never start
background inference, pull/delete models, or alter the user's Ollama settings.

Review generated source before `check`; its AST filter and child-process timeout
are not a security sandbox. Do not run untrusted candidates in GitHub Actions.

Run `python -m unittest discover -s tests -v` and
`python -m local_worker_bench selftest` before pushing. Keep first-pass and repaired
results separate. Passing these narrow fixtures does not qualify an application.
