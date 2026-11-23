# Disposable HTTP patch fixture

This intentionally broken tiny project tests a project-shaped patch workflow,
not a production application. Its 17 independent regression tests include eight
real loopback HTTP responses and nine direct type/validation cases. The local
model sees the function contract, not the regression test implementation.

Copy to a fresh ignored results directory, run the unchanged tests to record the
red baseline, and request the packet at `examples/paging/http-patch.packet.json`.
Inspect the returned function before applying it to only `accepted()` in the
disposable copy. Preserve source hashes, the exact replacement, baseline failures
and final test output. Then run `python -m unittest discover -s tests -v` in the
copy. Do not modify regression tests to make a candidate pass.

Never apply model output to this canonical broken fixture or count a hosted
rewrite as a local-model patch. A passing toy project is an additional practical
check, not evidence of autonomous production repository engineering.
