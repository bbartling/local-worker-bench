"""Print verified vs downloading models; no inference."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_worker_bench.model_readiness import WAVE_AFTER_DOWNLOAD, WAVE_READY_FIRST, partition


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--json', action='store_true')
    args = p.parse_args()
    report = partition(ROOT)
    report['policy'] = {
        'ready_first': list(WAVE_READY_FIRST),
        'after_download': list(WAVE_AFTER_DOWNLOAD),
        'unready_poll_seconds': 3600,
        'inference_paused': (ROOT / 'INFERENCE_PAUSED').exists(),
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    print('Ready now (test first):')
    for item in report['ready']:
        print(f"  {item['alias']:22} verified")
    print('Still downloading (later; hour sleep when due):')
    for item in report['waiting']:
        pct = item.get('pct')
        print(f"  {item['alias']:22} {pct}% " if pct is not None else f"  {item['alias']:22} no status")
    print('INFERENCE_PAUSED:', report['policy']['inference_paused'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
