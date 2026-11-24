import json
import io
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from local_worker_bench.native_stream import collect,request
from local_worker_bench.runner import api,InferenceError


def event(content=None,finish=None,**extra):
    return ('data: '+json.dumps({'choices':[{'index':0,'delta':{'content':content},'finish_reason':finish}],**extra})+'\n').encode()


class NativeCaptureTests(unittest.TestCase):
    def test_timeout_error_keeps_receipt_pointer_for_partial_files(self):
        receipt='a'*32
        error=urllib.error.HTTPError('http://127.0.0.1/api/chat',504,'timeout',{},
            io.BytesIO(json.dumps({'error':'deadline','resource_receipt':receipt}).encode()))
        with patch('urllib.request.OpenerDirector.open',side_effect=error):
            with self.assertRaises(InferenceError) as caught:api('http://127.0.0.1','/api/chat',{},1)
        self.assertEqual(caught.exception.resource_receipt,receipt)

    def test_live_http_prefix_is_saved_before_final_response(self):
        release=threading.Event();results=[];errors=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                self.server.body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                self.wfile.write(event('hello ')+b'\n');self.wfile.flush()
                release.wait(timeout=4)
                self.wfile.write(event('world')+event(finish='stop')+b'data: [DONE]\n\n');self.wfile.flush()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                def run():
                    try:results.append(request(server.server_port,{'model':'synthetic'},5,root))
                    except Exception as error:errors.append(error)
                client=threading.Thread(target=run,daemon=True);client.start()
                try:
                    end=time.monotonic()+3
                    while time.monotonic()<end and not (root/'partial.txt').exists():time.sleep(.01)
                    while time.monotonic()<end and (root/'partial.txt').read_text()!='hello ':time.sleep(.01)
                    self.assertEqual((root/'partial.txt').read_text(),'hello ')
                    self.assertTrue(client.is_alive());self.assertTrue(server.body['stream'])
                finally:release.set();client.join(timeout=5)
                self.assertFalse(errors);self.assertEqual(results[0]['choices'][0]['message']['content'],'hello world')
        finally:release.set();server.shutdown();server.server_close();thread.join(timeout=3)

    def test_complete_stream_preserves_content_and_timing(self):
        with tempfile.TemporaryDirectory() as directory:
            usage=('data: '+json.dumps({'choices':[],'usage':{'completion_tokens':2},'timings':{'predicted_ms':10}})+'\n').encode()
            lines=[event('hello '),event('world'),event(finish='stop'),usage,b'data: [DONE]\n']
            result=collect(iter(lines),Path(directory))
            self.assertEqual(result['choices'][0]['message']['content'],'hello world')
            self.assertEqual(result['timings']['predicted_ms'],10)
            self.assertEqual((Path(directory)/'partial.txt').read_text(),'hello world')

    def test_disconnect_keeps_flushed_prefix_and_is_not_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def interrupted():
                yield event('unfinished')
                self.assertEqual((root/'partial.txt').read_text(),'unfinished')
                raise OSError('synthetic connection loss')
            with self.assertRaises(OSError):collect(interrupted(),root)
            self.assertEqual((root/'partial.txt').read_text(),'unfinished')
            self.assertEqual(len((root/'events.jsonl').read_text().splitlines()),1)

    def test_eof_without_done_is_never_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'without final completion'):
                collect(iter([event('candidate',finish='stop')]),Path(directory))
