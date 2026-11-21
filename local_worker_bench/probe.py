"""Read-only HTTP/API probes. No model or SDK."""
import json, time
import urllib.request, urllib.error, urllib.parse

def validate_probe(p):
    errors=[]
    if p['status'] not in p['expected_statuses']: errors.append('status')
    if p.get('expect_json'):
        try:
            data=json.loads(p['body'])
            if not isinstance(data, dict): errors.append('json_object')
            elif data.get('ok') is False: errors.append('soft_error')
            elif 'expected_id' in p and data.get('id') != p['expected_id']: errors.append('id')
        except (ValueError,TypeError): errors.append('json')
    return errors

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def probe(spec):
    url=spec['url']; parsed=urllib.parse.urlsplit(url)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password: raise ValueError('Use an HTTP(S) URL without embedded credentials.')
    method=spec.get('method','GET').upper()
    if method not in ('GET','HEAD'): raise ValueError('Only GET/HEAD are supported.')
    expected=spec.get('expected_statuses',[200])
    if not isinstance(expected,list) or not expected or any(type(s) is not int or not 100<=s<=599 for s in expected): raise ValueError('expected_statuses must be a nonempty list of HTTP status integers.')
    began=time.monotonic(); r={'id':spec.get('id',url),'url':url,'method':method,'expected_statuses':expected,'expect_json':bool(spec.get('expect_json',False)),'browser_tested':False}
    if 'expected_id' in spec:
        if not r['expect_json']: raise ValueError('expected_id requires expect_json')
        r['expected_id'] = spec['expected_id']
    try:
        try: response=urllib.request.build_opener(NoRedirect()).open(urllib.request.Request(url,method=method),timeout=10)
        except urllib.error.HTTPError as e: response=e
        with response:
            raw=response.read(1048577)
            r.update(status=response.code,content_type=response.headers.get('Content-Type',''),location=response.headers.get('Location'),body=raw[:1048576].decode('utf-8','replace'))
        if len(raw)>1048576: r.update(errors=['response_too_large'],passed=False,truncated=True)
        else:
            errors=validate_probe(r); r.update(errors=errors,passed=not errors,truncated=False)
        r['body_excerpt']=r.pop('body')[:2000]
    except (OSError,urllib.error.URLError) as e: r.update(status=None,passed=False,errors=['network'],network_error=str(e))
    r['seconds']=round(time.monotonic()-began,3); return r
