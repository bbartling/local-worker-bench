"""Synthetic GGUF metadata tests; no model weights or inference."""
from pathlib import Path
import struct
import tempfile
import unittest

from scripts.plan_gguf_partitions import inspect, plan


def text(value):
    raw=value.encode();return struct.pack('<Q',len(raw))+raw


def fixture(path,bad_offset=False):
    sizes=[32,32,96,32,32,96,32,32]
    names=['token_embd.weight',*[f'blk.{i}.weight' for i in range(6)],'output.weight']
    header=b'GGUF'+struct.pack('<IQQ',3,len(names),1)+text('general.alignment')+struct.pack('<II',4,32)
    offset=0
    for name,size in zip(names,sizes):
        header+=text(name)+struct.pack('<IQIQ',1,size//4,0,99999 if bad_offset else offset)
        offset+=size
    start=(len(header)+31)//32*32
    path.write_bytes(header+b'\0'*(start-len(header))+b'\0'*offset)
    return sum(sizes)


class GgufPlanTests(unittest.TestCase):
    def test_storage_accounted_and_groups_cover_every_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'synthetic.gguf';size=fixture(path)
            parsed=inspect(path);result=plan([parsed])
            self.assertEqual(result['total_tensor_span_bytes'],size)
            self.assertEqual(sum(g['serialized_span_bytes'] for g in result['groups']),size)
            self.assertEqual([i for g in result['groups'] for i in range(g['layers'][0],g['layers'][1]+1)],list(range(6)))
            self.assertTrue(result['plan_only']);self.assertFalse(result['inference_started'])
            self.assertLessEqual(max(g['serialized_span_bytes'] for g in result['groups']),192)

    def test_invalid_offsets_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'synthetic.gguf';fixture(path,True)
            with self.assertRaises(ValueError):inspect(path)

    def test_duplicate_splits_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'synthetic.gguf';fixture(path);parsed=inspect(path)
            with self.assertRaises(ValueError):plan([parsed,parsed])

    def test_truncated_header_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'synthetic.gguf';path.write_bytes(b'GGUF\x03')
            with self.assertRaises(ValueError):inspect(path)
