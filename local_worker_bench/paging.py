"""Read-only host detection and OS-paging budgets. No model loading or slicing."""
import ctypes
import math
import mmap
import os
from pathlib import Path
import platform

from . import memory


def host_snapshot():
    observed=memory.available_memory()
    if os.name=='nt':
        total=ctypes.c_ulonglong()
        if not ctypes.windll.kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(total)):
            raise ctypes.WinError()
        total_bytes=total.value*1024
    elif platform.system()=='Linux':
        total_bytes=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemTotal:')))*1024
    else:raise ValueError('Supported planning targets: Windows and Linux')
    return dict(observed,total_bytes=total_bytes,os=platform.system(),cpu=platform.processor(),
        logical_cpus=os.cpu_count(),page_bytes=mmap.PAGESIZE,
        wsl='microsoft' in platform.release().lower(),
        enforcement='Windows process working set' if os.name=='nt' else 'monitor only; cgroup setup required separately')


def plan(snapshot,model_bytes,fraction=.66):
    if type(model_bytes) is not int or model_bytes<=0:raise ValueError('Positive model byte count required')
    if isinstance(fraction,bool) or not isinstance(fraction,(int,float)) or not math.isfinite(fraction) or not .1<=fraction<=.66:
        raise ValueError('Use a finite fraction from 0.10 through 0.66')
    available=snapshot['available_bytes'];total=snapshot['total_bytes']
    reserve=max(2*memory.GIB,int(total*.1))
    budget=min(int(available*fraction),available-reserve,24*memory.GIB)
    if budget<memory.GIB:raise ValueError('Insufficient available RAM above reserve')
    return {'host':snapshot,'fraction_of_available':fraction,'working_set_bytes':budget,
        'reserve_bytes':reserve,'model_bytes':model_bytes,
        'weight_to_budget_ratio':round(model_bytes/budget,3),
        'equivalent_budget_chunks':math.ceil(model_bytes/budget),
        'physical_model_slices_created':0,
        'meaning':'Chunks are a capacity illustration only. The OS pages mapped weights; no fixed slices are loaded in sequence.',
        'warning':'Working set is not total host/cache/commit use. Linux cgroup accounting differs; neither is a fit guarantee.'}


def verified_files(manifest):
    if manifest.get('all_sha256_verified') is not True:raise ValueError('Require a completed verified manifest')
    files=[]
    for item in manifest['files']:
        path=Path(item['local_path']).resolve()
        if not path.is_file() or path.stat().st_size!=item['bytes']:raise ValueError('Artifact missing or size changed')
        with path.open('rb') as stream:
            if stream.read(4)!=b'GGUF':raise ValueError('Expected GGUF')
        files.append(str(path))
    if not files:raise ValueError('Empty manifest')
    return files
