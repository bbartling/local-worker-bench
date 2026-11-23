"""Opt-in, loopback-only Ollama subset over a memory-mapped llama.cpp worker.

Only explicitly registered, already-downloaded GGUFs may be used. Each request
owns one native process; a watchdog and finally block stop it. No generated code
execution, pulls, provider changes, streaming, or automatic model escalation.
"""
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid

from . import memory
from .runner import worker_lock
from .streaming import summarize as summarize_streaming, verified as verified_streaming


class ApiError(Exception):
    def __init__(self,message,status=400): super().__init__(message); self.status=status


def read_config(path):
    config=json.loads(path.read_text(encoding='utf-8-sig'))
    exe=Path(config['backend_executable']).expanduser()
    if not exe.is_absolute(): exe=(path.parent/exe).resolve()
    if not exe.is_file(): raise ValueError('Native backend executable does not exist.')
    config['backend_executable']=str(exe)
    models=config.get('models')
    if not isinstance(models,dict) or not models: raise ValueError('Register at least one model.')
    for name,profile in models.items():
        if not isinstance(name,str) or not name or len(name)>100: raise ValueError('Invalid model alias.')
        if type(profile.setdefault('layer_stream',False)) is not bool: raise ValueError('layer_stream must be a bool.')
        files=profile.get('files')
        if not isinstance(files,list) or not files: raise ValueError('Register all GGUF split files, in order.')
        profile['files']=[str((path.parent/Path(f)).resolve()) if not Path(f).is_absolute() else f for f in files]
        for key,default,low,high in [('threads',4,1,4),('context',2048,512,8192),('max_tokens',640,1,1024),
                                    ('request_timeout',600,5,1800),('load_timeout',180,5,600),
                                    ('working_set_gib',8,0.05,24),('reserve_gib',6,2,24),
                                    ('private_limit_gib',6 if profile['layer_stream'] else 16,1,16)]:
            value=profile.setdefault(key,default)
            if isinstance(value,bool) or not isinstance(value,(float,int)) or not low<=value<=high: raise ValueError('Invalid model profile setting: '+key)
            if key not in ('working_set_gib','reserve_gib','private_limit_gib') and type(value) is not int: raise ValueError('Integer setting required: '+key)
    return config


def files_ready(profile):
    for name in profile['files']:
        path=Path(name)
        if not path.is_file(): return False
        with path.open('rb') as f:
            if f.read(4)!=b'GGUF': return False
    return True


def backend_request(port,path,body=None,timeout=5):
    request=urllib.request.Request(f'http://127.0.0.1:{port}'+path,
        None if body is None else json.dumps(body).encode(),{'Content-Type':'application/json'})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request,timeout=timeout) as response:
            raw=response.read(2*1024**2+1)
        if len(raw)>2*1024**2: raise ApiError('Native response too large.',502)
        return json.loads(raw)
    except urllib.error.HTTPError as e:
        raise ApiError('Native backend error: '+e.read(2000).decode('utf-8','replace'),502) from e


def validate_chat(body,models):
    if not isinstance(body,dict): raise ApiError('Expected a JSON object.')
    if body.get('stream',False) is not False: raise ApiError('This bounded API supports stream:false only.')
    if any(key in body for key in ('tools','images','keep_alive_forever')): raise ApiError('Tools/images are not supported.')
    model=body.get('model')
    if model not in models: raise ApiError('Unknown registered model; no download attempted.',404)
    profile=models[model]; messages=body.get('messages')
    if not isinstance(messages,list) or not 1<=len(messages)<=20: raise ApiError('Use 1 to 20 messages.')
    chars=0
    for item in messages:
        if not isinstance(item,dict) or item.get('role') not in ('system','user','assistant') or not isinstance(item.get('content'),str): raise ApiError('Use plain text system/user/assistant messages.')
        if set(item)-{'role','content'}: raise ApiError('Unsupported message fields.')
        chars+=len(item['content'])
    if chars>12000: raise ApiError('Trim messages to 12000 characters.',413)
    options=body.get('options',{})
    if not isinstance(options,dict) or set(options)-{'num_thread','num_ctx','num_predict','temperature','presence_penalty','repeat_penalty','seed'}: raise ApiError('Unsupported generation option.')
    if options.get('num_thread',profile['threads'])!=profile['threads']: raise ApiError('Thread count is fixed by the registered profile.')
    if options.get('num_ctx',profile['context'])!=profile['context']: raise ApiError('Context size is fixed by the registered profile.')
    tokens=options.get('num_predict',profile['max_tokens'])
    if type(tokens) is not int or not 1<=tokens<=profile['max_tokens']: raise ApiError('Output token budget exceeds profile.')
    if body.get('think',False) is not False: raise ApiError('This worker uses non-thinking mode.')
    native={'model':model,'messages':messages,'stream':False,'max_tokens':tokens,
            'temperature':0,'presence_penalty':0,'cache_prompt':False,
            'chat_template_kwargs':{'enable_thinking':False}}
    fmt=body.get('format')
    if fmt=='json': native['response_format']={'type':'json_object'}
    elif isinstance(fmt,dict): native['response_format']={'type':'json_schema','json_schema':{'name':'candidate','schema':fmt}}
    elif fmt is not None: raise ApiError('format must be json or a JSON schema.')
    return model,profile,native


class Manager:
    def __init__(self,config,results,monitored_only=False):
        self.config=config; self.results=Path(results); self.monitored_only=monitored_only
        self.lock=threading.Lock(); self.cancel=threading.Event(); self.active=None
        self.process=None; self.shutting_down=False; self.finished=threading.Event(); self.finished.set()

    def shutdown(self):
        self.shutting_down=True; self.cancel.set()
        process=self.process
        if process is not None and process.poll() is None:
            try:
                process.terminate(); process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
            except OSError: pass
        self.finished.wait(timeout=10)

    def observe(self,process,profile,samples,began):
        if self.cancel.is_set(): raise ApiError('Request canceled by unload.',409)
        if process.poll() is not None: raise ApiError('Owned native worker exited; inspect its receipt/log.',502)
        global_mem=memory.available_memory(); process_mem=memory.process_memory(process.pid)
        sample=dict(seconds=round(time.monotonic()-began,3),**global_mem,**process_mem); samples.append(sample)
        if global_mem['available_bytes']<profile['reserve_gib']*memory.GIB: raise ApiError('Free RAM fell below the desktop reserve; worker stopped.',503)
        if global_mem['available_commit_bytes'] is not None and global_mem['available_commit_bytes']<memory.GIB: raise ApiError('System commit reserve is low; worker stopped.',503)
        private_limit=profile.get('private_limit_gib',6 if profile.get('layer_stream',False) else 16)
        if process_mem['private_bytes']>private_limit*memory.GIB: raise ApiError(f'Worker private memory exceeded {private_limit} GiB; stopped.',503)
        if process_mem['rss_bytes']>(profile['working_set_gib']+0.25)*memory.GIB: raise ApiError('Worker exceeded the observed residency limit; stopped.',503)

    def chat(self,body):
        if self.shutting_down: raise ApiError('Service is shutting down.',503)
        model,profile,native=validate_chat(body,self.config['models'])
        if not files_ready(profile): raise ApiError('Registered GGUF files are not ready. Downloads are separate.',503)
        if not self.lock.acquire(blocking=False): raise ApiError('One worker is already running; request not queued.',429)
        self.finished.clear()
        try:
            if self.shutting_down: raise ApiError('Service is shutting down.',503)
            try:
                # The bench client already holds inference.lock while waiting
                # for this API. Use a separate cross-server engine lease.
                with worker_lock('offload-engine.lock'): return self._chat(model,profile,native)
            except ValueError as e: raise ApiError(str(e),409) from e
        finally: self.lock.release(); self.finished.set()

    def _chat(self,model,profile,native):
        if memory.available_memory()['available_bytes']<profile['reserve_gib']*memory.GIB+memory.GIB: raise ApiError('Not enough RAM above the desktop reserve to start.',503)
        self.cancel.clear(); request_id=uuid.uuid4().hex
        folder=self.results/request_id; folder.mkdir(parents=True,exist_ok=False)
        receipt={'id':request_id,'model':model,'started_utc':datetime.now(timezone.utc).isoformat(),
                 'profile':{k:v for k,v in profile.items() if k!='files'},'samples':[],
                 'mode':'memory-mapped CPU; no repacking; one native process per request','code_executed':False}
        with socket.socket() as sock: sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
        command=[self.config['backend_executable'],'--model',profile['files'][0],
            '--alias',model,'--host','127.0.0.1','--port',str(port),'--threads',str(profile['threads']),
            '--threads-batch',str(profile['threads']),'--ctx-size',str(profile['context']),
            '--parallel','1','--gpu-layers','0','--device','none','--fit','off',
            '--load-mode','mmap','--lazy-mode','on','--no-repack','--no-warmup','--cache-ram','0']
        if profile.get('layer_stream',False):command+=['--log-verbosity','5']
        process=None; began=time.monotonic()
        try:
            env={k:v for k,v in os.environ.items() if not k.startswith('LLAMA_ARG_')}
            env.update(OMP_NUM_THREADS=str(profile['threads']),MKL_NUM_THREADS=str(profile['threads']),OPENBLAS_NUM_THREADS=str(profile['threads']))
            env['LWB_DISABLE_MMAP_PREFETCH']='1'
            env['LWB_LAYER_STREAM']='1' if profile.get('layer_stream',False) else '0'
            receipt['bulk_prefetch_disable_requested']=True
            with (folder/'backend.log').open('w',encoding='utf-8') as log:
                process=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                self.process=process
                self.active={'model':model,'pid':process.pid,'request_id':request_id}
                if self.monitored_only: receipt['working_set_limit']={'hard_working_set_limit':False}
                else: receipt['working_set_limit']=memory.set_working_set_limit(process.pid,int(profile['working_set_gib']*memory.GIB))
                deadline=began+profile['load_timeout']
                while True:
                    self.observe(process,profile,receipt['samples'],began)
                    try:
                        if backend_request(port,'/health',timeout=.5).get('status')=='ok': break
                    except (OSError,ApiError): pass
                    if time.monotonic()>deadline: raise ApiError('Native model load timed out.',504)
                    time.sleep(.25)
                receipt['load_seconds']=round(time.monotonic()-began,3)
                receipt['bulk_prefetch_disable_confirmed']='LWB: bulk mmap prefetch disabled' in (folder/'backend.log').read_text(encoding='utf-8',errors='replace')
                channel=queue.Queue()
                def send():
                    try: channel.put((True,backend_request(port,'/v1/chat/completions',native,profile['request_timeout'])))
                    except Exception as e: channel.put((False,e))
                threading.Thread(target=send,daemon=True).start(); deadline=time.monotonic()+profile['request_timeout']
                while True:
                    self.observe(process,profile,receipt['samples'],began)
                    try: good,value=channel.get(timeout=.25)
                    except queue.Empty:
                        if time.monotonic()>deadline: raise ApiError('Generation timed out; owned worker stopped.',504)
                        continue
                    if not good:
                        if isinstance(value,ApiError): raise value
                        raise ApiError('Native request failed: '+str(value),502)
                    break
                choices=value.get('choices',[])
                if len(choices)!=1 or not isinstance(choices[0].get('message',{}).get('content'),str): raise ApiError('Native worker did not return one text candidate.',502)
                choice=choices[0]; usage=value.get('usage',{}); timings=value.get('timings',{})
                receipt.update(status='completed',native_finish_reason=choice.get('finish_reason'),usage=usage,timings=timings)
                return {'model':model,'created_at':datetime.now(timezone.utc).isoformat(),'message':{'role':'assistant','content':choice['message']['content']},
                    'done':True,'done_reason':'stop' if choice.get('finish_reason')=='stop' else 'length',
                    'total_duration':int((time.monotonic()-began)*1e9),'load_duration':int(receipt['load_seconds']*1e9),
                    'prompt_eval_count':usage.get('prompt_tokens'),'eval_count':usage.get('completion_tokens'),
                    'prompt_eval_duration':int(timings.get('prompt_ms',0)*1e6),'eval_duration':int(timings.get('predicted_ms',0)*1e6),
                    'resource_receipt':request_id,'code_executed':False}
        except Exception as e:
            receipt.update(status='error',error=str(e)); raise
        finally:
            if process is not None:
                if process.poll() is None: process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
                receipt['worker_exited']=process.poll() is not None
            self.active=None; self.process=None; receipt['seconds']=round(time.monotonic()-began,3)
            if receipt['samples']:
                receipt['summary']={'peak_rss_gib':max(s['rss_bytes'] for s in receipt['samples'])/memory.GIB,
                    'minimum_available_ram_gib':min(s['available_bytes'] for s in receipt['samples'])/memory.GIB}
            streaming_error=False
            if profile.get('layer_stream',False):
                receipt['streaming']=summarize_streaming((folder/'backend.log').read_text(encoding='utf-8',errors='replace'))
                streaming_error=receipt.get('status')=='completed' and not verified_streaming(receipt['streaming'])
                if streaming_error:receipt.update(status='error',error='Requested layer streaming was not verified in backend trace.')
            (folder/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
            if streaming_error:raise ApiError('Requested layer streaming was not verified; inspect receipt.',502)


def handler_for(manager):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def reply(self,status,body):
            data=json.dumps(body).encode(); self.send_response(status); self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data))); self.end_headers()
            try: self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError): pass
        def allowed(self):
            if self.headers.get('Origin'): self.reply(403,{'error':'Browser-origin requests are not supported.'}); return False
            return True
        def do_GET(self):
            if not self.allowed(): return
            models=[{'name':name,'model':name,'available':files_ready(p),'size':sum(Path(f).stat().st_size for f in p['files'] if Path(f).is_file()),'digest':p.get('digest')} for name,p in manager.config['models'].items()]
            if self.path=='/api/tags': self.reply(200,{'models':[m for m in models if m['available']]})
            elif self.path=='/api/ps': self.reply(200,{'models':[] if manager.active is None else [manager.active]})
            elif self.path in ('/health','/api/version'): self.reply(200,{'status':'ok','version':'local-worker-bench-offload-1','active':manager.active,'profiles':models})
            elif self.path=='/v1/models': self.reply(200,{'object':'list','data':[{'id':m['name'],'object':'model','owned_by':'local'} for m in models if m['available']]})
            else: self.reply(404,{'error':'Unknown endpoint.'})
        def do_POST(self):
            try:
                # Drain a bounded request before closing an Origin-rejected
                # connection; unread POST bytes can discard the reply on Windows.
                self.connection.settimeout(10)
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=1024**2: raise ApiError('Use a JSON body no larger than 1 MiB.',413)
                raw=self.rfile.read(length)
                if not self.allowed(): return
                body=json.loads(raw)
                if not isinstance(body,dict): raise ApiError('Expected JSON object.')
                if self.path=='/api/generate':
                    if set(body)-{'model','keep_alive'} or body.get('keep_alive')!=0 or body.get('model') not in manager.config['models']: raise ApiError('Only explicit unload is supported by /api/generate.')
                    if manager.active and manager.active['model']==body['model']: manager.cancel.set()
                    self.reply(200,{'done':True}); return
                if self.path!='/api/chat': raise ApiError('Unknown endpoint.',404)
                self.reply(200,manager.chat(body))
            except ApiError as e: self.reply(e.status,{'error':str(e)})
            except (OSError,ValueError,TypeError,KeyError) as e: self.reply(400,{'error':str(e)})
            except Exception: self.reply(500,{'error':'Worker failure; inspect local receipt.'})
    return Handler


def serve(args):
    config=read_config(args.config.resolve()); manager=Manager(config,args.results,args.monitored_only)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler_for(manager)); server.daemon_threads=True
    print(json.dumps({'endpoint':f'http://127.0.0.1:{server.server_port}','inference_started':False}),flush=True)
    try: server.serve_forever()
    finally: manager.shutdown(); server.server_close()
    return 0
