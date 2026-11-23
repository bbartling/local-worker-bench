"""Handwritten independent regression cases; loopback HTTP only."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import client

ROUTES={
    '/ok':(200,{'ok':True,'id':'worker-1'},True),
    '/false':(200,{'ok':False,'id':'worker-1'},False),
    '/wrong-id':(200,{'ok':True,'id':'worker-2'},False),
    '/numeric-ok':(200,{'ok':1,'id':'worker-1'},False),
    '/list':(200,[{'ok':True,'id':'worker-1'}],False),
    '/missing-id':(200,{'ok':True},False),
    '/unavailable':(503,{'ok':True,'id':'worker-1'},False),
    '/malformed':(200,b'not JSON',False),
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        status,payload,_=ROUTES[self.path]
        raw=payload if isinstance(payload,bytes) else json.dumps(payload).encode()
        self.send_response(status);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)


class ClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=3)


def http_case(route,expected):
    def test(self):
        url=f'http://127.0.0.1:{self.server.server_port}'+route
        self.assertIs(client.check_endpoint(url,'worker-1'),expected)
    return test


for route,(_,_,expected) in ROUTES.items():
    setattr(ClientTests,'test_http_'+route[1:].replace('-','_'),http_case(route,expected))


def direct_case(status,payload,expected_id,expected):
    def test(self):
        if expected is ValueError:
            with self.assertRaises(ValueError):client.accepted(status,payload,expected_id)
        else:self.assertIs(client.accepted(status,payload,expected_id),expected)
    return test


DIRECT={
    'status_float':(200.0,{'ok':True,'id':'worker-1'},'worker-1',False),
    'status_string':('200',{'ok':True,'id':'worker-1'},'worker-1',False),
    'status_bool':(True,{'ok':True,'id':'worker-1'},'worker-1',False),
    'status_201':(201,{'ok':True,'id':'worker-1'},'worker-1',False),
    'payload_none':(200,None,'worker-1',False),
    'payload_id_type':(200,{'ok':True,'id':1},'1',False),
    'expected_empty':(503,None,'',ValueError),
    'expected_none':(200,{'ok':True,'id':'worker-1'},None,ValueError),
    'expected_bool':(200,{'ok':True,'id':'worker-1'},True,ValueError),
}
for name,args in DIRECT.items():setattr(ClientTests,'test_'+name,direct_case(*args))
