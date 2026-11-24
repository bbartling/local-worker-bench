"""Persist native SSE deltas while preserving the public non-streaming API.

Partial text is diagnostic draft data, never a completed/accepted candidate.
"""
import json
from pathlib import Path
import time
import urllib.request

LIMIT=2*1024**2


def collect(lines,folder):
    folder=Path(folder);began=time.monotonic();content=[];size=0;finish=None;usage={};timings={};done=False
    with (folder/'partial.txt').open('w',encoding='utf-8') as text, (folder/'events.jsonl').open('w',encoding='utf-8') as events:
        for raw in lines:
            size+=len(raw)
            if size>LIMIT:raise ValueError('Native event stream exceeds 2 MiB')
            line=raw.decode('utf-8').strip()
            if not line or line.startswith(':'):continue
            if not line.startswith('data:'):continue
            payload=line[5:].strip()
            if payload=='[DONE]':done=True;break
            event=json.loads(payload)
            if not isinstance(event,dict) or event.get('error'):raise ValueError('Native stream returned an error')
            choices=event.get('choices',[])
            if not isinstance(choices,list) or len(choices)>1:raise ValueError('Expected one streamed choice')
            clean=[]
            for choice in choices:
                if choice.get('index',0)!=0:raise ValueError('Unexpected streamed choice index')
                delta=choice.get('delta',{});piece=delta.get('content')
                if piece is not None:
                    if not isinstance(piece,str):raise ValueError('Expected text delta')
                    content.append(piece);text.write(piece);text.flush()
                if choice.get('finish_reason') is not None:finish=choice['finish_reason']
                clean.append({'index':0,'delta':{'content':piece},'finish_reason':choice.get('finish_reason')})
            if isinstance(event.get('usage'),dict):usage=event['usage']
            if isinstance(event.get('timings'),dict):timings=event['timings']
            # Do not retain raw reasoning or proposed tool calls.
            events.write(json.dumps({'seconds':round(time.monotonic()-began,3),'choices':clean,
                'usage':event.get('usage'),'timings':event.get('timings')})+'\n');events.flush()
        if not done or finish is None:raise ValueError('Native stream ended without final completion; partial retained')
    return {'choices':[{'message':{'content':''.join(content)},'finish_reason':finish}],
        'usage':usage,'timings':timings}


def request(port,body,timeout,folder):
    native=dict(body,stream=True,stream_options={'include_usage':True})
    req=urllib.request.Request(f'http://127.0.0.1:{port}/v1/chat/completions',json.dumps(native).encode(),
        {'Content-Type':'application/json','Accept':'text/event-stream'})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req,timeout=timeout) as response:
        def lines():
            while True:
                line=response.readline(LIMIT+1)
                if not line:break
                yield line
        return collect(lines(),folder)
