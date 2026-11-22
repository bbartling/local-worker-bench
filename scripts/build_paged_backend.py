"""Build a pinned private CPU/RPC backend with optional Windows prefetch disable.

Fetches only build sources from the upstream commit, verifies Git blob hashes,
and writes beneath an ignored output directory. Never changes installed Ollama.
Requires CMake and a C++ toolchain. No model download or inference.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import urllib.request

COMMIT='94f3af3d09e74a0fb35f703194318d3b4037714a'


def wanted(path):
    if '/' not in path: return path in ('CMakeLists.txt','LICENSE','README.md','AGENTS.md')
    if path.startswith(('cmake/','common/','src/','include/','vendor/','tools/','ui/','scripts/')): return True
    if path.startswith('ggml/'):
        tail=path[5:]
        return ('/' not in tail or tail.startswith(('cmake/','include/','src/ggml-cpu/','src/ggml-rpc/'))
                or (tail.startswith('src/') and '/' not in tail[4:]))
    return False


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('results/paged-backend'))
    p.add_argument('--cmake',required=True); p.add_argument('--generator',default='Visual Studio 18 2026')
    p.add_argument('--fetch-only',action='store_true'); p.add_argument('--jobs',type=int,choices=range(1,5),default=4)
    args=p.parse_args(); source=args.output/'source'; source.mkdir(parents=True,exist_ok=True)
    tree_path=args.output/'upstream-tree.json'
    if not tree_path.exists():
        with urllib.request.urlopen('https://api.github.com/repos/ggml-org/llama.cpp/git/trees/'+COMMIT+'?recursive=1',timeout=30) as r: tree=json.load(r)
        if tree.get('truncated'): raise ValueError('Upstream tree was truncated.')
        tree_path.write_text(json.dumps(tree))
    tree=json.loads(tree_path.read_text())
    entries=[e for e in tree['tree'] if e['type']=='blob' and wanted(e['path'])]
    print(f'Fetching {len(entries)} pinned build-source files.',flush=True)
    def fetch(item):
        relative=PurePosixPath(item['path'])
        if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe upstream path.')
        target=source/Path(*relative.parts); target.resolve().relative_to(source.resolve())
        def valid(data): return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==item['sha']
        if target.is_file() and valid(target.read_bytes()): return
        url='https://raw.githubusercontent.com/ggml-org/llama.cpp/'+COMMIT+'/'+item['path']
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url,timeout=30) as r: data=r.read(item['size']+1)
                if len(data)!=item['size'] or not valid(data): raise ValueError('Upstream blob verification failed.')
                target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data); return
            except OSError:
                if attempt==2: raise
    with ThreadPoolExecutor(max_workers=12) as pool:
        for i,future in enumerate(as_completed([pool.submit(fetch,e) for e in entries]),1):
            future.result()
            if i%100==0: print(f'Verified {i}/{len(entries)} source files',flush=True)
    path=source/'src/llama-mmap.cpp'; text=path.read_text(encoding='utf-8')
    marker='        GGML_UNUSED(numa);\n\n        size = file->size();'
    replacement='''        GGML_UNUSED(numa);

        const char * disable_prefetch = std::getenv("LWB_DISABLE_MMAP_PREFETCH");
        if (disable_prefetch && disable_prefetch[0] == '1') {
            prefetch = 0;
            LLAMA_LOG_INFO("LWB: bulk mmap prefetch disabled\\n");
        }

        size = file->size();'''
    if text.count(marker)!=1: raise ValueError('Pinned mmap patch context does not match.')
    text=text.replace(marker,replacement)
    if '#include <cstdlib>' not in text: text='#include <cstdlib>\n'+text
    path.write_text(text,encoding='utf-8',newline='\n')
    provenance={'upstream_commit':COMMIT,'patch':'Opt-in Windows initial mmap prefetch disable through LWB_DISABLE_MMAP_PREFETCH=1',
                'patched_mmap_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (args.output/'source-provenance.json').write_text(json.dumps(provenance,indent=2))
    if args.fetch_only: return
    build=args.output/'build'
    command=[args.cmake,'-S',str(source.resolve()),'-B',str(build.resolve()),'-G',args.generator,'-A','x64',
        '-DGGML_RPC=ON','-DLLAMA_BUILD_TESTS=OFF','-DLLAMA_BUILD_EXAMPLES=OFF',
        '-DLLAMA_BUILD_APP=OFF','-DLLAMA_BUILD_UI=OFF','-DLLAMA_BUILD_HTML=OFF','-DLLAMA_USE_PREBUILT_UI=OFF',
        '-DLLAMA_BUILD_TOOLS=ON','-DLLAMA_BUILD_SERVER=ON','-DGGML_NATIVE=ON',
        '-DLLAMA_BUILD_NUMBER=12359','-DLLAMA_BUILD_COMMIT='+COMMIT[:8]]
    subprocess.run(command,check=True)
    subprocess.run([args.cmake,'--build',str(build.resolve()),'--config','Release','--target','llama-server','ggml-rpc-server','--parallel',str(args.jobs)],check=True)
    executables=list(build.rglob('llama-server.exe'))
    if len(executables)!=1: raise RuntimeError('Expected one native server executable.')
    provenance['executable']=str(executables[0].resolve())
    provenance['executable_sha256']=hashlib.sha256(executables[0].read_bytes()).hexdigest()
    (args.output/'build-provenance.json').write_text(json.dumps(provenance,indent=2))
    print(json.dumps(provenance,indent=2),flush=True)


if __name__=='__main__': main()
