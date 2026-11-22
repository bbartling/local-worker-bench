"""OS observations and an opt-in Windows hard working-set maximum.

Working-set residency is not total commit, virtual address space, or file cache.
This changes only the explicitly owned worker process, never global OS settings.
"""
import ctypes
import os
from pathlib import Path

GIB=2**30


def available_memory():
    if os.name=='nt':
        class Status(ctypes.Structure):
            _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in
                ('total_physical','available_physical','total_commit','available_commit','total_virtual','available_virtual','extended')]
        status=Status(); status.length=ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)): raise ctypes.WinError()
        return {'available_bytes':status.available_physical,'available_commit_bytes':status.available_commit}
    info={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if ':' in line and len(line.split())>=2}
    return {'available_bytes':info['MemAvailable'],'available_commit_bytes':None}


def windows_handle(pid,rights):
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]; kernel.CloseHandle.restype=wintypes.BOOL
    handle=kernel.OpenProcess(rights,False,pid)
    if not handle: raise ctypes.WinError(ctypes.get_last_error())
    return kernel,handle


def set_working_set_limit(pid,maximum_bytes):
    if os.name!='nt': raise RuntimeError('Hard working-set limits are implemented for Windows only; use --monitored-only explicitly on other systems.')
    from ctypes import wintypes
    kernel,handle=windows_handle(pid,0x0100|0x0400)  # SET_QUOTA | QUERY_INFORMATION
    try:
        fn=kernel.SetProcessWorkingSetSizeEx
        fn.argtypes=[wintypes.HANDLE,ctypes.c_size_t,ctypes.c_size_t,wintypes.DWORD]; fn.restype=wintypes.BOOL
        if not fn(handle,16*1024**2,int(maximum_bytes),0x00000004|0x00000002): raise ctypes.WinError(ctypes.get_last_error())
        low=ctypes.c_size_t(); high=ctypes.c_size_t(); flags=wintypes.DWORD()
        get=kernel.GetProcessWorkingSetSizeEx
        get.argtypes=[wintypes.HANDLE,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(wintypes.DWORD)]
        get.restype=wintypes.BOOL
        if not get(handle,ctypes.byref(low),ctypes.byref(high),ctypes.byref(flags)): raise ctypes.WinError(ctypes.get_last_error())
        if not flags.value&4 or high.value>maximum_bytes+65536: raise RuntimeError('Windows did not confirm the requested hard working-set limit.')
        return {'hard_working_set_limit':True,'maximum_bytes':high.value,'flags':flags.value}
    finally: kernel.CloseHandle(handle)


def process_memory(pid):
    if os.name=='nt':
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('page_faults',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in
                ('peak_rss','rss','peak_paged_pool','paged_pool','peak_nonpaged_pool','nonpaged_pool','pagefile','peak_pagefile','private_bytes')]
        kernel,handle=windows_handle(pid,0x0400|0x0010)
        try:
            counter=Counters(); counter.cb=ctypes.sizeof(counter)
            fn=ctypes.WinDLL('psapi',use_last_error=True).GetProcessMemoryInfo
            fn.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]; fn.restype=wintypes.BOOL
            if not fn(handle,ctypes.byref(counter),counter.cb): raise ctypes.WinError(ctypes.get_last_error())
            return {'rss_bytes':counter.rss,'private_bytes':counter.private_bytes,'page_faults':counter.page_faults}
        finally: kernel.CloseHandle(handle)
    values={}
    for line in Path(f'/proc/{pid}/status').read_text().splitlines():
        if line.startswith(('VmRSS:','RssAnon:')): values[line.split(':')[0]]=int(line.split()[1])*1024
    return {'rss_bytes':values.get('VmRSS',0),'private_bytes':values.get('RssAnon',0),'page_faults':None}
