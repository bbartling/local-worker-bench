import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('precision_extension',Path(__file__).resolve().parents[1]/'scripts/queue_precision_extension.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class PrecisionExtensionTests(unittest.TestCase):
    def test_requires_finished_parent_and_both_verified_models(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);legacy=root/'legacy';legacy.mkdir();cache=root/'cache';cache.mkdir()
            (legacy/'campaign.json').write_text(json.dumps({'trials':{}}))
            for model in ('qwen38-standard-q4','qwen38-f16'):
                dest=cache/model;dest.mkdir()
                (dest/'verified-manifest.json').write_text(json.dumps({'all_sha256_verified':True}))
            self.assertFalse(module.ready(legacy,cache))
            (legacy/'campaign.json').write_text(json.dumps({'finished_epoch':123}))
            self.assertTrue(module.ready(legacy,cache))
            (cache/'qwen38-f16/verified-manifest.json').write_text(json.dumps({'all_sha256_verified':False}))
            self.assertFalse(module.ready(legacy,cache))

    def test_header_gate_rejects_bf16_mislabeled_as_fp16(self):
        with tempfile.TemporaryDirectory() as folder:
            cache=Path(folder)
            for name in ('qwen38-standard-q4','qwen38-f16'):
                dest=cache/name;dest.mkdir()
                (dest/'verified-manifest.json').write_text(json.dumps({'repo':'fixture/model','revision':'a'*40,'all_sha256_verified':True}))
            def header(path,extra_keys=()):
                return {'metadata':{'tokenizer.chat_template':'same'},'file_bytes':100,
                    'tensors':[{'name':'weight','shape':[2,2],'ggml_type':12 if str(path)=='q4' else 30}]}
            with patch.object(module,'verified_files',side_effect=[['q4'],['f16']]),patch.object(module,'inspect',side_effect=header):
                with self.assertRaisesRegex(ValueError,'unexpected tensor types'):module.inspect_pair(cache)


if __name__=='__main__':unittest.main()
