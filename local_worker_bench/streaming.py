"""Parse owned-backend layer-residency receipts. No model/runtime dependencies."""
import json
import re


def summarize(text):
    events=[json.loads(line) for line in re.findall(r'LWB_STREAM (\{[^\n]+\})',text)]
    match=re.search(r'\bn_layer\s*=\s*(\d+)',text)
    expected=int(match.group(1)) if match else None
    layers=sorted({e['layer'] for e in events if not e['final']})
    return {'events':events,'eviction_requests':sum(e['eviction_requests'] for e in events),
        'unexpected_errors':sum(e['unexpected_errors'] for e in events),
        'sampled_resident_before':sum(e['resident_samples_before'] for e in events),
        'sampled_resident_after':sum(e['resident_samples_after'] for e in events),
        'decoder_layers_observed':layers,'expected_layer_count':expected,
        'all_decoder_layers_observed':expected is not None and layers==list(range(expected)),
        'semantics':'Explicit mapped-weight working-set eviction after decoder layers; virtual mappings and native KV/recurrent state preserved.'}


def verified(summary):
    return bool(summary['events'] and summary['all_decoder_layers_observed'] and summary['eviction_requests'] and not summary['unexpected_errors']
        and summary['sampled_resident_before']>summary['sampled_resident_after'])
