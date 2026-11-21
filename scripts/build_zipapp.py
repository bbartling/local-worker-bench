"""Build a dependency-free client archive for a host without GitHub access."""
import argparse
from pathlib import Path
import shutil
import tempfile
import zipapp

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
    parser.error('Output already exists; choose a new path.')
args.output.parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='local-worker-build-') as scratch:
    stage = Path(scratch)
    shutil.copytree(Path(__file__).resolve().parents[1] / 'local_worker_bench',
                    stage / 'local_worker_bench', ignore=shutil.ignore_patterns('__pycache__'))
    (stage / '__main__.py').write_text(
        'from local_worker_bench.cli import main\nraise SystemExit(main())\n', encoding='utf-8')
    zipapp.create_archive(stage, args.output, interpreter='/usr/bin/env python3', compressed=True)
print(args.output)
