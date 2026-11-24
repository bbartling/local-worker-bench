"""Offline worker lifecycle/API tests. No models, downloads, or generated code."""
from contextlib import nullcontext
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from local_worker_bench import memory, offload_api, runner


class FakeProcess:
    pid=12345
    def __init__(self): self.returncode=None
    def poll(self): return self.returncode
    def terminate(self): self.returncode=-15
    def kill(self): self.returncode=-9
    def wait(self,timeout=None): self.returncode=0; return 0


class OffloadTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.model=self.root/'fixture.gguf'; self.model.write_bytes(b'GGUFsynthetic')
        config={'backend_executable':sys.executable,'models':{'fixture':{'files':['fixture.gguf']}}}
        path=self.root/'config.json'; path.write_text(json.dumps(config)); self.config=offload_api.read_config(path)
        self.manager=offload_api.Manager(self.config,self.root/'receipts')
        self.body={'model':'fixture','stream':False,'messages':[{'role':'user','content':'Synthetic test'}]}

    def test_config_fixed_budgets(self):
        p=self.config['models']['fixture']; self.assertEqual(p['threads'],4); self.assertEqual(p['context'],2048)
        self.assertTrue(offload_api.files_ready(p))

    def test_explicit_eight_thread_profile_keeps_request_fixed_to_profile(self):
        path=self.root/'eight-config.json'
        config={'backend_executable':sys.executable,'models':{'fixture':{'files':[str(self.model)],'threads':8}}}
        path.write_text(json.dumps(config));models=offload_api.read_config(path)['models']
        offload_api.validate_chat(dict(self.body,options={'num_thread':8}),models)
        with self.assertRaises(offload_api.ApiError):
            offload_api.validate_chat(dict(self.body,options={'num_thread':4}),models)
        config['models']['fixture']['threads']=9;path.write_text(json.dumps(config))
        with self.assertRaises(ValueError):offload_api.read_config(path)

    def test_explicit_overnight_timeout_is_bounded(self):
        path=self.root/'long-config.json'
        config={'backend_executable':sys.executable,'models':{'fixture':{'files':[str(self.model)],'request_timeout':21600}}}
        path.write_text(json.dumps(config));self.assertEqual(offload_api.read_config(path)['models']['fixture']['request_timeout'],21600)
        config['models']['fixture']['request_timeout']=21601;path.write_text(json.dumps(config))
        with self.assertRaises(ValueError):offload_api.read_config(path)

    def test_sampler_settings_are_not_silently_ignored(self):
        for options in ({'temperature':.8},{'temperature':True},{'seed':42},{'repeat_penalty':1.2}):
            with self.subTest(options=options),self.assertRaises(offload_api.ApiError):
                offload_api.validate_chat(dict(self.body,options=options),self.config['models'])

    def test_request_budgets_and_no_tools(self):
        invalid=[{'stream':True},{'options':{'num_thread':8}},{'options':{'num_ctx':8192}},
                 {'options':{'num_predict':1025}},{'tools':[]},{'think':True},
                 {'format':'yaml'},{'messages':[{'role':'user','content':'x'*12001}]}]
        for override in invalid:
            with self.subTest(override=next(iter(override))), self.assertRaises(offload_api.ApiError):
                offload_api.validate_chat(dict(self.body,**override),self.config['models'])
        _,_,native=offload_api.validate_chat(dict(self.body,format='json'),self.config['models'])
        self.assertEqual(native['response_format'],{'type':'json_object'})
        self.assertFalse(native['chat_template_kwargs']['enable_thinking'])

    def test_missing_artifact_does_not_start_worker(self):
        self.model.unlink()
        with patch.object(offload_api.subprocess,'Popen') as spawn, self.assertRaises(offload_api.ApiError): self.manager.chat(self.body)
        spawn.assert_not_called()

    def test_concurrent_request_not_queued(self):
        self.manager.lock.acquire()
        try:
            with self.assertRaises(offload_api.ApiError) as error: self.manager.chat(self.body)
            self.assertEqual(error.exception.status,429)
        finally: self.manager.lock.release()

    def test_client_lease_does_not_deadlock_server_lease(self):
        with patch.object(runner.Path,'home',return_value=self.root), \
             patch.object(self.manager,'_chat',return_value={'done':True}):
            with runner.worker_lock():
                self.assertEqual(self.manager.chat(self.body),{'done':True})
                self.assertTrue((self.root/'.cache/local-worker-bench/inference.lock').exists())
            self.assertFalse((self.root/'.cache/local-worker-bench/offload-engine.lock').exists())

    def run_fake(self,reply=None,low_after_start=False,load_error=False,limit_error=False,private_bytes=100,health_delay=0):
        process=FakeProcess()
        available={'available_bytes':20*memory.GIB,'available_commit_bytes':20*memory.GIB}
        low=dict(available,available_bytes=memory.GIB)
        def native(port,path,body=None,timeout=5):
            if path=='/apply-template':return {'prompt':'Synthetic rendered prompt'}
            if path=='/tokenize':return {'tokens':[1,2,3,4,5]}
            if path=='/health':
                if health_delay:
                    import time
                    time.sleep(health_delay)
                if load_error: raise OSError('Synthetic unready')
                return {'status':'ok'}
            if isinstance(reply,Exception): raise reply
            return reply or {'choices':[{'message':{'content':'{"candidate":true}'},'finish_reason':'stop'}],
                             'usage':{'prompt_tokens':5,'completion_tokens':7}}
        if load_error: self.config['models']['fixture']['load_timeout']=0
        limit=OSError('Synthetic quota failure') if limit_error else {'hard_working_set_limit':True,'maximum_bytes':8*memory.GIB}
        with patch.object(offload_api,'worker_lock',return_value=nullcontext()), \
             patch.object(offload_api.subprocess,'Popen',return_value=process) as spawn, \
             patch.object(offload_api,'backend_request',side_effect=native), \
             patch.object(memory,'available_memory',side_effect=[available,low] if low_after_start else lambda:available), \
             patch.object(memory,'process_memory',return_value={'rss_bytes':memory.GIB,'private_bytes':private_bytes,'page_faults':10}), \
             patch.object(memory,'set_working_set_limit',side_effect=limit if limit_error else None,return_value=limit):
            try: result=self.manager.chat(self.body)
            finally:
                self.assertIsNotNone(process.poll()); self.assertIsNone(self.manager.active)
                receipts=list((self.root/'receipts').glob('*/receipt.json')); self.assertEqual(len(receipts),1)
                self.assertTrue(json.loads(receipts[0].read_text())['worker_exited'])
        return result,spawn.call_args.args[0]

    def test_native_flags_receipt_and_cleanup(self):
        result,command=self.run_fake(); self.assertEqual(result['done_reason'],'stop'); self.assertFalse(result['code_executed'])
        self.assertIn('--no-repack',command); self.assertIn('--no-warmup',command)
        self.assertEqual(command[command.index('--load-mode')+1],'mmap')
        self.assertEqual(command[command.index('--threads')+1],'4')

    def test_loading_consumes_request_deadline_before_generation(self):
        self.config['models']['fixture'].update(capture_partial=True,request_timeout=.01)
        with patch('local_worker_bench.native_stream.request') as send:
            with self.assertRaisesRegex(offload_api.ApiError,'before generation'):self.run_fake(health_delay=.03)
        send.assert_not_called()

    def test_stream_disconnect_retains_partial_and_error_receipt(self):
        self.config['models']['fixture']['capture_partial']=True
        def interrupted(port,body,timeout,folder):
            (folder/'partial.txt').write_text('unfinished',encoding='utf-8')
            raise OSError('synthetic disconnect')
        with patch('local_worker_bench.native_stream.request',side_effect=interrupted):
            with self.assertRaises(offload_api.ApiError) as error:self.run_fake()
        self.assertTrue(error.exception.resource_receipt)
        receipt=json.loads(next((self.root/'receipts').glob('*/receipt.json')).read_text())
        self.assertFalse(receipt['partial_capture']['complete'])
        self.assertEqual(receipt['partial_capture']['bytes'],10)
        self.assertTrue(receipt['worker_exited'])

    def test_context_admission_preserves_output_room(self):
        self.config['models']['fixture']['validate_context']=True
        _,command=self.run_fake()
        self.assertIn('--no-context-shift',command)
        receipt=json.loads(next((self.root/'receipts').glob('*/receipt.json')).read_text())
        self.assertEqual(receipt['context_admission']['prompt_tokens'],5)

    def test_context_overflow_stops_worker_before_generation(self):
        profile=self.config['models']['fixture'];profile.update(validate_context=True,context=512,max_tokens=512)
        with self.assertRaisesRegex(offload_api.ApiError,'exceeds context'):self.run_fake()

    def test_streaming_profile_fails_closed_without_backend_evidence(self):
        self.config['models']['fixture']['layer_stream']=True
        with self.assertRaisesRegex(offload_api.ApiError,'not verified'):self.run_fake()

    def test_streaming_profile_accepts_verified_layer_trace(self):
        from local_worker_bench.streaming import summarize
        row=dict(layer=0,final=False,eviction_requests=1,unexpected_errors=0,
            resident_samples_before=3,resident_samples_after=0)
        summary=summarize('n_layer = 1\nLWB_STREAM '+json.dumps(row)+'\n')
        self.config['models']['fixture']['layer_stream']=True
        with patch.object(offload_api,'summarize_streaming',return_value=summary):
            result,command=self.run_fake()
        self.assertEqual(result['done_reason'],'stop')
        self.assertEqual(command[command.index('--log-verbosity')+1],'5')

    def test_resource_guard_stops_owned_worker(self):
        with self.assertRaisesRegex(offload_api.ApiError,'reserve'): self.run_fake(low_after_start=True)

    def test_registered_private_memory_budget_stops_owned_worker(self):
        self.config['models']['fixture']['private_limit_gib']=1
        with self.assertRaisesRegex(offload_api.ApiError,'private memory'):self.run_fake(private_bytes=2*memory.GIB)

    def test_load_timeout_stops_owned_worker(self):
        with self.assertRaisesRegex(offload_api.ApiError,'load timed out'): self.run_fake(load_error=True)

    def test_backend_failure_stops_owned_worker(self):
        with self.assertRaisesRegex(offload_api.ApiError,'Native request failed'): self.run_fake(reply=OSError('Synthetic network failure'))

    def test_quota_failure_stops_owned_worker(self):
        with self.assertRaisesRegex(OSError,'quota failure'): self.run_fake(limit_error=True)

    def test_truncation_is_not_a_pass(self):
        result,_=self.run_fake(reply={'choices':[{'message':{'content':'partial'},'finish_reason':'length'}]})
        self.assertEqual(result['done_reason'],'length')

    def test_live_loopback_routes_without_inference(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),offload_api.handler_for(self.manager))
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            with urllib.request.urlopen(base+'/api/tags') as response: self.assertEqual(json.load(response)['models'][0]['name'],'fixture')
            with urllib.request.urlopen(base+'/api/ps') as response: self.assertEqual(json.load(response)['models'],[])
            request=urllib.request.Request(base+'/api/chat',json.dumps(dict(self.body,stream=True)).encode(),{'Content-Type':'application/json'})
            with self.assertRaises(urllib.error.HTTPError) as error: urllib.request.urlopen(request)
            self.assertEqual(error.exception.code,400)
            error.exception.close()
            request=urllib.request.Request(base+'/api/chat',json.dumps(self.body).encode(),{'Content-Type':'application/json','Origin':'https://example.test'})
            with self.assertRaises(urllib.error.HTTPError) as error: urllib.request.urlopen(request)
            self.assertEqual(error.exception.code,403)
            error.exception.close()
            with self.assertRaisesRegex(ValueError,'stream:false'):
                runner.api(base,'/api/chat',dict(self.body,stream=True))
        finally: server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_shutdown_refuses_new_work(self):
        self.manager.shutdown()
        with self.assertRaisesRegex(offload_api.ApiError,'shutting down'): self.manager.chat(self.body)

    def test_generation_timeout_stops_owned_worker(self):
        self.config['models']['fixture']['request_timeout']=.1
        def slow(port,path,body=None,timeout=5):
            if path=='/health': return {'status':'ok'}
            threading.Event().wait(.4)
            return {'choices':[{'message':{'content':'late'},'finish_reason':'stop'}]}
        process=FakeProcess()
        with patch.object(offload_api,'worker_lock',return_value=nullcontext()), \
             patch.object(offload_api.subprocess,'Popen',return_value=process), \
             patch.object(offload_api,'backend_request',side_effect=slow), \
             patch.object(memory,'available_memory',return_value={'available_bytes':20*memory.GIB,'available_commit_bytes':20*memory.GIB}), \
             patch.object(memory,'process_memory',return_value={'rss_bytes':1,'private_bytes':1,'page_faults':0}), \
             patch.object(memory,'set_working_set_limit',return_value={'hard_working_set_limit':True}):
            with self.assertRaisesRegex(offload_api.ApiError,'Generation timed out'): self.manager.chat(self.body)
        self.assertIsNotNone(process.poll()); self.assertIsNone(self.manager.active)

    @unittest.skipUnless(os.name=='nt','Windows quota API')
    def test_actual_windows_limit_on_owned_idle_process(self):
        child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)'])
        try:
            limit=memory.set_working_set_limit(child.pid,64*1024**2)
            self.assertTrue(limit['hard_working_set_limit']); self.assertLessEqual(limit['maximum_bytes'],64*1024**2)
            self.assertGreater(memory.process_memory(child.pid)['rss_bytes'],0)
        finally: child.terminate(); child.wait(timeout=5)


class DownloadManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('download_gguf',Path(__file__).resolve().parents[1]/'scripts/download_gguf.py')
        cls.module=importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.module)

    def test_manifest_paths_and_budget_metadata(self):
        manifest=json.loads((Path(__file__).resolve().parents[1]/'examples/offload/qwen3-coder-next-q4.download.json').read_text())
        items=self.module.entries(manifest,Path('results/models'))
        self.assertEqual(len(items),4); self.assertEqual(sum(i['bytes'] for i,_,_ in items),48410992032)
        for item,target,url in items: self.assertTrue(url.startswith('https://huggingface.co/Qwen/'))
        for bad in ('../escape.gguf','/absolute.gguf','C:/escape.gguf','script.py','..\\escape.gguf'):
            manifest['files'][0]['path']=bad
            with self.subTest(path=bad), self.assertRaises(ValueError): self.module.entries(manifest,Path('results/models'))

    def test_dotted_model_repo_allowed_but_traversal_rejected(self):
        manifest=json.loads((Path(__file__).resolve().parents[1]/'examples/paging/qwen38-q4.download.json').read_text())
        self.assertEqual(len(self.module.entries(manifest,Path('results/models'))),1)
        for repo in ('../bad','user/../bad','user/a..b','https://bad/model'):
            manifest['repo']=repo
            with self.subTest(repo=repo),self.assertRaises(ValueError):self.module.entries(manifest,Path('results/models'))


if __name__=='__main__': unittest.main()
