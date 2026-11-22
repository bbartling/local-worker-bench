# Working on this tool

Use synthetic fixtures only. Never commit application credentials, private logs,
model weights, or customer data. Keep generated results under ignored `results/`.

Model calls require an explicit user request for the current task. Use four
threads by default and one local worker at a time. The portable `ask` client
unloads afterward; the locked Mint OptiPlex host may keep `qwen3.5:4b` and
`qwen3-coder:30b` warm (`MAX_LOADED_MODELS=2`, `KEEP_ALIVE=-1`) per
`docs/linux-mint-4b-30b-setup.md`. Never start background inference, pull/delete
models, or alter the user's Ollama settings unless the current task explicitly
asks for that.

Review generated source before `check`; its AST filter and child-process timeout
are not a security sandbox. Do not run untrusted candidates in GitHub Actions.

Run `python -m unittest discover -s tests -v` and
`python -m local_worker_bench selftest` before pushing. Keep first-pass and repaired
results separate. Passing these narrow fixtures does not qualify an application.
