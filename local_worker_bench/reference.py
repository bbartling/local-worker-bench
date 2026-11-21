"""Hand-written fixture controls, not production HVAC algorithms."""
def motor_gate(kind, proofs, required=True):
    if type(required) is not bool: raise ValueError('required')
    if required is False: return 'ACTIVE'
    if kind not in ('ahu','pump') or not isinstance(proofs,dict): raise ValueError('shape')
    states=proofs.get('supply_fan' if kind=='ahu' else 'pumps',[])
    if not isinstance(states,(list,tuple)) or any(v is not None and type(v) is not bool for v in states): raise ValueError('proof')
    if any(v is True for v in states): return 'ACTIVE'
    if states and all(v is False for v in states): return 'INACTIVE'
    return 'UNKNOWN'

import math
def fault_hours(samples,max_gap_s):
    if type(max_gap_s) not in (int,float) or not math.isfinite(max_gap_s) or max_gap_s<=0: raise ValueError('gap')
    if not isinstance(samples,list): raise ValueError('samples')
    by_time={}
    for row in samples:
        if not isinstance(row,(list,tuple)) or len(row)!=3: raise ValueError('row')
        t,f,a=row
        if type(t) not in (int,float) or not math.isfinite(t): raise ValueError('time')
        if any(v is not None and type(v) is not bool for v in (f,a)): raise ValueError('state')
        by_time[t]=(f,a)
    keys=sorted(by_time)
    fault=covered=0.0
    for i in range(len(keys)-1):
        f,a=by_time[keys[i]]
        dt=min(keys[i+1]-keys[i],max_gap_s)
        if a is True and type(f) is bool:
            covered+=dt
            if f is True: fault+=dt
    return fault/3600,covered/3600
