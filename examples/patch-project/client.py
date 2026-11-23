"""Synthetic patch fixture. accepted() is intentionally wrong; tests should fail."""
import json
import urllib.error
import urllib.request


def accepted(status, payload, expected_id):
    return status == 200 and bool(payload)


def check_endpoint(url, expected_id):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url,timeout=3) as response:
            status=response.status;raw=response.read(4096)
    except urllib.error.HTTPError as error:
        status=error.code;raw=error.read(4096)
    try:payload=json.loads(raw.decode('utf-8'))
    except (ValueError,UnicodeError):payload=None
    return accepted(status,payload,expected_id)
