"""Pi-friendly authenticated API gateway. HTTP forwarding only, no inference.

The upstream is fixed at startup (normally an SSH tunnel to a compute worker).
This module never spawns a process, downloads weights, or imports an ML runtime.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import secrets
import threading
import urllib.error

from .runner import api, endpoint_url


def make_handler(upstream,token,timeout=1800):
    gate=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def reply(self,status,result):
            raw=json.dumps(result).encode(); self.send_response(status); self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw))); self.end_headers()
            try: self.wfile.write(raw)
            except (BrokenPipeError,ConnectionResetError): pass
        def authorized(self):
            if self.headers.get('Origin'): self.reply(403,{'error':'Browser-origin requests are not supported.'}); return False
            supplied=self.headers.get('Authorization','').encode('utf-8')
            if not secrets.compare_digest(supplied,('Bearer '+token).encode('utf-8')):
                self.reply(401,{'error':'Bearer token required.'}); return False
            return True
        def do_GET(self):
            if self.path=='/health': self.reply(200,{'status':'ok','role':'control-plane-gateway','inference_on_controller':False}); return
            if not self.authorized(): return
            if self.path not in ('/api/tags','/api/ps','/api/version'): self.reply(404,{'error':'Unknown endpoint.'}); return
            try: self.reply(200,api(upstream,self.path,timeout=10))
            except (OSError,ValueError): self.reply(502,{'error':'Compute-worker API unavailable; controller has no inference fallback.'})
        def do_POST(self):
            acquired=False
            try:
                # Consume a bounded body before closing a rejected connection.
                # Closing with unread POST bytes can reset TCP on Windows and
                # discard the authentication response before the client sees it.
                self.connection.settimeout(10)
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=1024**2: self.reply(413,{'error':'Use a JSON body of at most 1 MiB.'}); return
                raw=self.rfile.read(length)
                if not self.authorized(): return
                if self.path not in ('/api/chat','/api/generate'): self.reply(404,{'error':'Unknown endpoint.'}); return
                body=json.loads(raw)
                if not isinstance(body,dict): self.reply(400,{'error':'Expected a JSON object.'}); return
                if self.path=='/api/chat':
                    acquired=gate.acquire(blocking=False)
                    if not acquired: self.reply(429,{'error':'One compute request is active; no implicit queue.'}); return
                result=api(upstream,self.path,body,timeout=timeout)
                self.reply(200,dict(result,controller_inference=False))
            except (OSError,ValueError): self.reply(502,{'error':'Compute request failed; inspect the worker receipt. No local fallback was attempted.'})
            finally:
                if acquired: gate.release()
    return Handler


def serve(args):
    upstream=endpoint_url(args.upstream,getattr(args,'allow_lan_upstream',False))
    if args.host not in ('127.0.0.1','localhost'):
        try: private=ipaddress.ip_address(args.host).is_private
        except ValueError: private=False
        if not args.allow_lan_listen or not private: raise ValueError('Use loopback, or explicitly allow a private numeric LAN listen address.')
    path=args.token_file.resolve()
    if not path.is_file(): raise ValueError('Provide a local token file; never put the token in argv or git.')
    token=path.read_text(encoding='utf-8').strip()
    if not 24<=len(token)<=256 or not token.isascii(): raise ValueError('Use an ASCII token of 24 to 256 characters.')
    import os
    if os.name!='nt' and path.stat().st_mode&0o077: raise ValueError('Token file must not be group/world readable (chmod 600).')
    server=ThreadingHTTPServer((args.host,args.port),make_handler(upstream,token,args.timeout)); server.daemon_threads=True
    print(json.dumps({'endpoint':f'http://{args.host}:{server.server_port}','upstream':upstream,'inference_on_controller':False}),flush=True)
    try: server.serve_forever()
    finally: server.server_close()
    return 0
