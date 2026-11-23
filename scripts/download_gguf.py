"""Explicit, resumable public Hugging Face artifact download; never inference.

The manifest pins sizes and SHA256s. Files stay beneath the chosen output folder.
No credentials, remote Python code, model registry settings, or model deletion.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
import shutil
import threading
import time
import urllib.parse
import urllib.request


def entries(manifest, output):
    repo=manifest['repo']; revision=manifest['revision']
    if len(repo.split('/'))!=2 or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',part) or '..' in part for part in repo.split('/')):
        raise ValueError('Use a public Hugging Face owner/repo identifier.')
    if len(revision)!=40 or any(c not in '0123456789abcdef' for c in revision):
        raise ValueError('Pin a full revision SHA.')
    result=[]; seen=set()
    for item in manifest['files']:
        path=PurePosixPath(item['path'])
        if path.is_absolute() or '..' in path.parts or '\\' in str(path) or ':' in str(path) or path.suffix!='.gguf':
            raise ValueError('Only relative .gguf paths are allowed.')
        target=(output/Path(*path.parts)).resolve()
        target.relative_to(output.resolve())
        if target in seen or type(item['bytes']) is not int or item['bytes']<=0:
            raise ValueError('Duplicate path or invalid byte count.')
        seen.add(target)
        digest=item['sha256']
        if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest): raise ValueError('Invalid SHA256.')
        url='https://huggingface.co/'+repo+'/resolve/'+revision+'/'+urllib.parse.quote(str(path),safe='/')
        result.append((item,target,url))
    if not result: raise ValueError('Empty manifest.')
    return result


def digest_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--max-gb',type=float,default=60); parser.add_argument('--workers',type=int,choices=range(1,5),default=4)
    args=parser.parse_args(); manifest=json.loads(args.manifest.read_text(encoding='utf-8'))
    items=entries(manifest,args.output); total=sum(i['bytes'] for i,_,_ in items)
    if total>args.max_gb*1e9: raise ValueError('Manifest exceeds explicit download budget.')
    args.output.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(args.output).free<total+5*2**30: raise ValueError('Not enough disk space plus 5 GiB reserve.')
    progress={str(t):0 for _,t,_ in items}; lock=threading.Lock(); stopped=threading.Event(); errors=[]
    status=args.output/'download-status.json'
    def save():
        with lock:
            record={'model':manifest['model'],'total_bytes':total,'completed_bytes':sum(progress.values()),'inference_started':False,'errors':list(errors)}
            temp=status.with_suffix('.tmp'); temp.write_text(json.dumps(record,indent=2)); temp.replace(status)
    def fetch(entry):
        item,target,url=entry; target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            if target.stat().st_size!=item['bytes'] or digest_file(target)!=item['sha256']:
                raise ValueError('Existing artifact mismatch; inspect it rather than silently overwrite: '+str(target))
            progress[str(target)]=item['bytes']; return
        partial=target.with_suffix('.gguf.partial')
        for attempt in range(3):
            if stopped.is_set(): raise RuntimeError('Download canceled.')
            offset=partial.stat().st_size if partial.exists() else 0
            if offset>item['bytes']: raise ValueError('Partial file exceeds expected size.')
            progress[str(target)]=offset
            if offset==item['bytes']: break
            headers={'Range':f'bytes={offset}-'} if offset else {}
            try:
                with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=60) as response:
                    if offset and response.status==206:
                        if not response.headers.get('Content-Range','').startswith(f'bytes {offset}-'): raise ValueError('Incorrect resume range.')
                    elif response.status==200: offset=0
                    else: raise ValueError('Unexpected artifact response.')
                    with partial.open('ab' if offset else 'wb') as dest:
                        count=offset
                        while not stopped.is_set():
                            block=response.read(1024*1024)
                            if not block: break
                            count+=len(block)
                            if count>item['bytes']: raise ValueError('Artifact exceeds manifest size.')
                            dest.write(block)
                            with lock: progress[str(target)]=count
                if partial.stat().st_size==item['bytes']: break
            except OSError:
                if attempt==2: raise
                time.sleep(2)
        if partial.stat().st_size!=item['bytes'] or digest_file(partial)!=item['sha256']:
            raise ValueError('Downloaded artifact size/hash mismatch; partial preserved.')
        partial.replace(target)
        with lock: progress[str(target)]=item['bytes']
    def reporter():
        while not stopped.wait(10):
            save(); print(f'Download only: {sum(progress.values())/1e9:.2f}/{total/1e9:.2f} GB',flush=True)
    thread=threading.Thread(target=reporter,daemon=True); thread.start()
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            try:
                for future in [pool.submit(fetch,item) for item in items]: future.result()
            except BaseException:
                stopped.set()
                raise
        receipt={'model':manifest['model'],'repo':manifest['repo'],'revision':manifest['revision'],
                 'files':[dict(item,local_path=str(target.resolve())) for item,target,_ in items],'all_sha256_verified':True}
        (args.output/'verified-manifest.json').write_text(json.dumps(receipt,indent=2))
        print('All artifacts verified. No inference started.',flush=True)
    except BaseException as e:
        errors.append(str(e)); raise
    finally: stopped.set(); thread.join(timeout=2); save()


if __name__=='__main__': main()
