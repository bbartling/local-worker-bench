"""Create a separate pinned native layer-eviction backend; never inference.

Reuses the already verified source tree from build_paged_backend.py, verifies
the exact context patch site, and preserves the earlier baseline binaries.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

COMMIT='94f3af3d09e74a0fb35f703194318d3b4037714a'
ROOT=Path(__file__).resolve().parents[1]


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,default=Path('results/paged-backend'))
    p.add_argument('--output',type=Path,default=Path('results/layer-stream-backend'))
    p.add_argument('--cmake',required=True);args=p.parse_args()
    origin=args.source_root.resolve();output=args.output.resolve()
    if output.exists():raise ValueError('Use a new backend directory; preserve previous artifacts')
    tree=json.loads((origin/'upstream-tree.json').read_text())
    if tree['sha']!=COMMIT:raise ValueError('Unexpected source revision')
    raw=(origin/'source/src/llama-context.cpp').read_bytes()
    expected=next(e['sha'] for e in tree['tree'] if e['path']=='src/llama-context.cpp')
    if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=expected:
        raise ValueError('Context source differs from pinned upstream')
    output.mkdir(parents=True);source=output/'source';shutil.copytree(origin/'source',source)
    header=ROOT/'native/lwb_layer_stream_windows.h';shutil.copy2(header,source/'src/lwb-layer-stream.h')
    path=source/'src/llama-context.cpp';text=path.read_text(encoding='utf-8')
    site='        ggml_backend_sched_set_eval_callback(sched.get(), cparams.cb_eval, cparams.cb_eval_user_data);'
    if text.count(site)!=1:raise ValueError('Expected exactly one scheduler callback patch site')
    replacement='''#ifdef _WIN32
        if (lwb_layer_stream_enabled()) {
            if (cparams.cb_eval != nullptr) throw std::runtime_error("LWB streaming cannot replace an existing eval callback");
            ggml_backend_sched_set_eval_callback(sched.get(),lwb_layer_eval,const_cast<llama_model *>(&model));
        } else
#endif
        {
            ggml_backend_sched_set_eval_callback(sched.get(),cparams.cb_eval,cparams.cb_eval_user_data);
        }'''
    text=text.replace(site,replacement).replace('//\n// llama_context\n//','#include "lwb-layer-stream.h"\n\n//\n// llama_context\n//',1)
    if '#include "lwb-layer-stream.h"' not in text:raise ValueError('Missing header insertion')
    path.write_text(text,encoding='utf-8',newline='\n')
    provenance={'upstream_commit':COMMIT,'experiment':'Per-layer Windows mapped-weight working-set eviction; not virtual unmapping',
        'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),
        'patched_context_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (output/'source-provenance.json').write_text(json.dumps(provenance,indent=2))
    build=output/'build'
    subprocess.run([args.cmake,'-S',str(source),'-B',str(build),'-G','Visual Studio 18 2026','-A','x64',
        '-DGGML_RPC=ON','-DLLAMA_BUILD_TESTS=OFF','-DLLAMA_BUILD_EXAMPLES=OFF','-DLLAMA_BUILD_APP=OFF',
        '-DLLAMA_BUILD_UI=OFF','-DLLAMA_BUILD_HTML=OFF','-DLLAMA_USE_PREBUILT_UI=OFF',
        '-DLLAMA_BUILD_TOOLS=ON','-DLLAMA_BUILD_SERVER=ON','-DGGML_NATIVE=ON',
        '-DLLAMA_BUILD_NUMBER=12359','-DLLAMA_BUILD_COMMIT='+COMMIT[:8]],check=True)
    subprocess.run([args.cmake,'--build',str(build),'--config','Release','--target','llama-server','--parallel','4'],check=True)
    exe=build/'bin/Release/llama-server.exe'
    provenance['executable_sha256']=hashlib.sha256(exe.read_bytes()).hexdigest()
    provenance['llama_dll_sha256']=hashlib.sha256((exe.parent/'llama.dll').read_bytes()).hexdigest()
    (output/'build-provenance.json').write_text(json.dumps(provenance,indent=2));print(json.dumps(provenance),flush=True)
