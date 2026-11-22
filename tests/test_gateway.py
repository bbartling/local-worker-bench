"""Controller checks use a fake upstream; never inference."""
from http.server import ThreadingHTTPServer
import json
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from local_worker_bench.gateway import make_handler


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.token='synthetic-test-token-not-a-secret'
        self.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler('http://127.0.0.1:11447',self.token))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(5)

    def request(self,path,body=None,authenticated=True):
        headers={'Content-Type':'application/json'}
        if authenticated: headers['Authorization']='Bearer '+self.token
        request=urllib.request.Request(f'http://127.0.0.1:{self.server.server_port}'+path,
            data=None if body is None else json.dumps(body).encode(),headers=headers)
        try:
            with urllib.request.urlopen(request,timeout=5) as response:
                return response.status,json.load(response)
        except urllib.error.HTTPError as error:
            with error: return error.code,json.load(error)

    @patch('local_worker_bench.gateway.api')
    def test_health_never_calls_worker(self,api):
        status,body=self.request('/health',authenticated=False)
        self.assertEqual(status,200)
        self.assertFalse(body['inference_on_controller'])
        api.assert_not_called()

    @patch('local_worker_bench.gateway.api')
    def test_authentication_before_forwarding(self,api):
        self.assertEqual(self.request('/api/chat',{},False)[0],401)
        api.assert_not_called()

    @patch('local_worker_bench.gateway.api',return_value={'done':True})
    def test_chat_forwards_fixed_upstream(self,api):
        status,body=self.request('/api/chat',{'model':'synthetic'})
        self.assertEqual(status,200)
        self.assertFalse(body['controller_inference'])
        api.assert_called_once_with('http://127.0.0.1:11447','/api/chat',{'model':'synthetic'},timeout=1800)

    @patch('local_worker_bench.gateway.api',side_effect=OSError('offline'))
    def test_unreachable_worker_fails_closed(self,api):
        self.assertEqual(self.request('/api/chat',{'model':'synthetic'})[0],502)
        self.assertEqual(api.call_count,1)
