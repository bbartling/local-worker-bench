# Suite 3 + Typst paper Implementation Plan

> **For agentic workers:** cheap model (`composer-2.5-fast`) implements Suite 3 / resource defaults; parent + Grok evaluate. Inference remains paused (`INFERENCE_PAUSED`).

**Goal:** Mutation-qualified project-patch suite (v3) plus portable resource defaults, and a human-readable Typst research note (≤6 pages) explaining paging, GGUF, and supervised local patch cycling for Open-FDD-like work.

**Architecture:** Keep frozen v1 cases and published grades untouched. Add suite version 3 with stronger assertions, mutant CI gate, suite hash in grades, and clearer dispositions. New profiles may default toward .66 available-RAM / ~.66 CPU threads with overrides; never reinterpret old .40/4-thread results.

**Tech Stack:** Python 3, unittest, Typst, existing `local_worker_bench` + llama.cpp backend (no inference in this plan).

## Global Constraints

- Do not remove `INFERENCE_PAUSED` or start smoke/campaigns/inference.
- Do not modify `C:\Users\ben\Documents\open-fdd`.
- Do not edit frozen v1 grading cases or rescore old model outputs.
- Downloads may continue; do not start duplicate download writers.
- Commit small honest changes to main when asked; no force-push.
- Typst paper: 5–6 pages max, research style, honest about zero accepted pagination patches.

---

## Task A — Suite 3 graders + mutant CI (cheap model)

Files: `local_worker_bench/project_bench.py`, `tests/test_project_bench.py`, `scripts/check_project_patch.py`, `scripts/publish_project_results.py`

- [ ] Add `SUITE_VERSION = 3` and suite-source hash into `grade()` output; publish validates them.
- [ ] Stateful/request-aware pagination fake: assert full query logs on success paths (`pageSize=100`, offsets, filters retained on token pages).
- [ ] Negative cases: otherwise-valid bodies so wrong early raises cannot fake pass; assert fetch counts; no harness `AssertionError` converted to pass.
- [ ] Close holes from panel mutants: bool `totalCount` with one row, empty id, `max_pages=1.0`, completed page at exact cap, telemetry state `0`, export `False` / negative kPa sign.
- [ ] CI mutant corpus: listed wrong patches must score `passed < total`; keep always-raise calibration.
- [ ] Disposition helpers: timeout / needs_context / rejected / accepted / cancelled distinct (no conflating campaign stop with supervisor cancel if easy).
- [ ] Run `python -m unittest discover -s tests -v` and `python -m local_worker_bench selftest`.

## Task B — Resource defaults (cheap model)

Files: `local_worker_bench/offload_api.py`, `local_worker_bench/paging.py`, `scripts/prepare_project_bench.py`, `scripts/run_project_bench.py`, related tests

- [ ] Helper: default threads ≈ 66% of affinity-visible logical CPUs (min 1, ≤ exposed, record provenance).
- [ ] Raise API thread high bound past 8 for larger hosts; keep explicit overrides.
- [ ] Project prepare default memory_fraction `.66` for **new** configs; document that historical runs used `.40`.
- [ ] Deterministic tests for 1/2/8/12/large CPU selection.

## Task C — Typst paper (parent)

- [ ] `docs/reports/typst/main.typ` research note ≤6 pages.
- [ ] Compile to `docs/reports/os-paging-research.pdf`.
- [ ] Cover: custom code, OS paging, GGUF/Ollama/llama.cpp/tensors, tests, honest best results, Open-FDD patch-cycle vision.

## Task D — Grok final eval

- [ ] After A–C: Grok reviews suite mutants still fail appropriately and paper claims match evidence.
