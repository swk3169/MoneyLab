"""Windows implementation of the run watcher Platform (RUNWATCH-01 D2, D3, D7, D12).

Every kernel32 function has argtypes and restype; errors are read with use_last_error. Structure sizes are
checked against the x64 layout before anything is created. The job handle is created non-inheritable and is
never duplicated or passed to a child. Only the three standard handles are inherited (handle list attribute).
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
CREATE_SUSPENDED = 0x00000004
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
CREATE_NO_WINDOW = 0x08000000
STARTF_USESTDHANDLES = 0x00000100
PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x1
FILE_SHARE_WRITE = 0x2
CREATE_NEW = 1
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 0x102
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
RESUME_FAILED = 0xFFFFFFFF
MAX_WAIT_MS = 0xFFFFFFFE


class LayoutError(Exception):
    """A Win32 structure size differs from the x64 layout (D2)."""


class _BasicLimit(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]


class _IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in ("ReadOperationCount", "WriteOperationCount",
                                                       "OtherOperationCount", "ReadTransferCount",
                                                       "WriteTransferCount", "OtherTransferCount")]


class _ExtendedLimit(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", _BasicLimit), ("IoInfo", _IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


class _BasicAccounting(ctypes.Structure):
    _fields_ = [("TotalUserTime", ctypes.c_longlong), ("TotalKernelTime", ctypes.c_longlong),
                ("ThisPeriodTotalUserTime", ctypes.c_longlong), ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
                ("TotalPageFaultCount", wintypes.DWORD), ("TotalProcesses", wintypes.DWORD),
                ("ActiveProcesses", wintypes.DWORD), ("TotalTerminatedProcesses", wintypes.DWORD)]


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


class _StartupInfo(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR),
                ("lpTitle", wintypes.LPWSTR), ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD), ("dwXCountChars", wintypes.DWORD),
                ("dwYCountChars", wintypes.DWORD), ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
                ("lpReserved2", ctypes.c_void_p), ("hStdInput", wintypes.HANDLE),
                ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]


class _StartupInfoEx(ctypes.Structure):
    _fields_ = [("StartupInfo", _StartupInfo), ("lpAttributeList", ctypes.c_void_p)]


class _ProcessInformation(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]


class _SecurityAttributes(ctypes.Structure):
    _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p),
                ("bInheritHandle", wintypes.BOOL)]


EXPECTED_SIZES = {"JOBOBJECT_BASIC_LIMIT_INFORMATION": (_BasicLimit, 64), "IO_COUNTERS": (_IoCounters, 48),
                  "JOBOBJECT_EXTENDED_LIMIT_INFORMATION": (_ExtendedLimit, 144),
                  "JOBOBJECT_BASIC_ACCOUNTING_INFORMATION": (_BasicAccounting, 48),
                  "MEMORYSTATUSEX": (_MemoryStatusEx, 64), "STARTUPINFOW": (_StartupInfo, 104),
                  "STARTUPINFOEXW": (_StartupInfoEx, 112), "PROCESS_INFORMATION": (_ProcessInformation, 24),
                  "SECURITY_ATTRIBUTES": (_SecurityAttributes, 24)}


def check_layout() -> None:
    for name, (struct, size) in EXPECTED_SIZES.items():
        if ctypes.sizeof(struct) != size:
            raise LayoutError(f"{name} is {ctypes.sizeof(struct)} bytes, expected {size}")


@dataclass
class Child:
    process: int
    thread: int
    pid: int


def _kernel32() -> Any:
    if sys.platform != "win32":
        raise OSError("moneylab.runwatch.winjob requires Windows")
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    h, b, d, p = wintypes.HANDLE, wintypes.BOOL, wintypes.DWORD, ctypes.POINTER
    sig: dict[str, tuple[list[Any], Any]] = {
        "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], h),
        "SetInformationJobObject": ([h, ctypes.c_int, ctypes.c_void_p, d], b),
        "QueryInformationJobObject": ([h, ctypes.c_int, ctypes.c_void_p, d, p(d)], b),
        "AssignProcessToJobObject": ([h, h], b),
        "IsProcessInJob": ([h, h, p(b)], b),
        "TerminateJobObject": ([h, wintypes.UINT], b),
        "TerminateProcess": ([h, wintypes.UINT], b),
        "ResumeThread": ([h], d),
        "WaitForSingleObject": ([h, d], d),
        "GetExitCodeProcess": ([h, p(d)], b),
        "CloseHandle": ([h], b),
        "CreateFileW": ([wintypes.LPCWSTR, d, d, p(_SecurityAttributes), d, d, h], h),
        "InitializeProcThreadAttributeList": ([ctypes.c_void_p, d, d, p(ctypes.c_size_t)], b),
        "UpdateProcThreadAttribute": ([ctypes.c_void_p, d, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t,
                                       ctypes.c_void_p, p(ctypes.c_size_t)], b),
        "DeleteProcThreadAttributeList": ([ctypes.c_void_p], None),
        "CreateProcessW": ([wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, b, d,
                            ctypes.c_void_p, wintypes.LPCWSTR, p(_StartupInfoEx), p(_ProcessInformation)], b),
        "GlobalMemoryStatusEx": ([p(_MemoryStatusEx)], b),
    }
    for name, (args, res) in sig.items():
        fn = getattr(k, name)
        fn.argtypes = args
        fn.restype = res
    return k


def _fail(what: str) -> OSError:
    return OSError(f"{what} failed (Win32 error {ctypes.get_last_error()})")


class WinPlatform:
    """Platform protocol on Windows. Handles are plain ints owned by the watcher."""

    def __init__(self) -> None:
        check_layout()
        self.k = _kernel32()

    def available_memory(self) -> int:
        status = _MemoryStatusEx()
        status.dwLength = ctypes.sizeof(status)
        if not self.k.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise _fail("GlobalMemoryStatusEx")
        return int(status.ullAvailPhys)

    def create_job(self) -> int:
        job = self.k.CreateJobObjectW(None, None)          # no security attributes: not inheritable
        if not job:
            raise _fail("CreateJobObjectW")
        info = _ExtendedLimit()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.k.SetInformationJobObject(job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(info),
                                              ctypes.sizeof(info)):
            error = _fail("SetInformationJobObject")
            self.k.CloseHandle(job)
            raise error
        return int(job)

    def _open_file(self, path: str, access: int, share: int, disposition: int, inherit: bool) -> int:
        sa = _SecurityAttributes(ctypes.sizeof(_SecurityAttributes), None, inherit)
        handle = self.k.CreateFileW(path, access, share, ctypes.byref(sa), disposition, FILE_ATTRIBUTE_NORMAL, None)
        if handle is None or handle == INVALID_HANDLE_VALUE:
            raise _fail("CreateFileW")
        return int(handle)

    def start_suspended(self, argv: tuple[str, ...], cwd: Path, stdout_path: Path, stderr_path: Path) -> Child:
        app = argv[0] if os.path.isabs(argv[0]) else os.path.join(str(cwd), argv[0])
        handles: list[int] = []
        attr_buf: Any = None
        attr_ready = False
        try:
            handles.append(self._open_file("NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, OPEN_EXISTING,
                                           True))
            handles.append(self._open_file(str(stdout_path), GENERIC_WRITE, FILE_SHARE_READ, CREATE_NEW, True))
            handles.append(self._open_file(str(stderr_path), GENERIC_WRITE, FILE_SHARE_READ, CREATE_NEW, True))
            size = ctypes.c_size_t(0)
            self.k.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
            attr_buf = (ctypes.c_byte * size.value)()
            if not self.k.InitializeProcThreadAttributeList(attr_buf, 1, 0, ctypes.byref(size)):
                raise _fail("InitializeProcThreadAttributeList")
            attr_ready = True
            handle_array = (wintypes.HANDLE * 3)(*handles)
            if not self.k.UpdateProcThreadAttribute(attr_buf, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST, handle_array,
                                                    ctypes.sizeof(handle_array), None, None):
                raise _fail("UpdateProcThreadAttribute")
            siex = _StartupInfoEx()
            siex.StartupInfo.cb = ctypes.sizeof(_StartupInfoEx)
            siex.StartupInfo.dwFlags = STARTF_USESTDHANDLES
            siex.StartupInfo.hStdInput, siex.StartupInfo.hStdOutput, siex.StartupInfo.hStdError = handles
            siex.lpAttributeList = ctypes.cast(attr_buf, ctypes.c_void_p)
            info = _ProcessInformation()
            command = ctypes.create_unicode_buffer(subprocess.list2cmdline(list(argv)))
            flags = CREATE_SUSPENDED | EXTENDED_STARTUPINFO_PRESENT | CREATE_NO_WINDOW
            if not self.k.CreateProcessW(app, command, None, None, True, flags, None, str(cwd), ctypes.byref(siex),
                                         ctypes.byref(info)):
                raise _fail("CreateProcessW")
            return Child(process=int(info.hProcess), thread=int(info.hThread), pid=int(info.dwProcessId))
        finally:
            if attr_ready:
                self.k.DeleteProcThreadAttributeList(attr_buf)
            for handle in handles:
                self.k.CloseHandle(handle)

    def child_pid(self, child: Child) -> int:
        return child.pid

    def assign(self, job: int, child: Child) -> None:
        if not self.k.AssignProcessToJobObject(job, child.process):
            raise _fail("AssignProcessToJobObject")

    def in_job(self, job: int, child: Child) -> bool:
        result = wintypes.BOOL()
        if not self.k.IsProcessInJob(child.process, job, ctypes.byref(result)):
            raise _fail("IsProcessInJob")
        return bool(result.value)

    def resume(self, child: Child) -> None:
        if self.k.ResumeThread(child.thread) == RESUME_FAILED:
            raise _fail("ResumeThread")

    def wait_child(self, child: Child, seconds: float) -> bool:
        ms = max(0, min(int(seconds * 1000), MAX_WAIT_MS))
        rc = self.k.WaitForSingleObject(child.process, ms)
        if rc == WAIT_OBJECT_0:
            return True
        if rc == WAIT_TIMEOUT:
            return False
        raise _fail(f"WaitForSingleObject returned {rc:#x}")

    def exit_code(self, child: Child) -> int:
        code = wintypes.DWORD()
        if not self.k.GetExitCodeProcess(child.process, ctypes.byref(code)):
            raise _fail("GetExitCodeProcess")
        return int(code.value)

    def job_active(self, job: int) -> int:
        info = _BasicAccounting()
        if not self.k.QueryInformationJobObject(job, JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION, ctypes.byref(info),
                                                ctypes.sizeof(info), None):
            raise _fail("QueryInformationJobObject(BasicAccounting)")
        return int(info.ActiveProcesses)

    def job_peak_commit(self, job: int) -> int:
        info = _ExtendedLimit()
        if not self.k.QueryInformationJobObject(job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(info),
                                                ctypes.sizeof(info), None):
            raise _fail("QueryInformationJobObject(ExtendedLimit)")
        return int(info.PeakJobMemoryUsed)

    def terminate_job(self, job: int) -> None:
        if not self.k.TerminateJobObject(job, 1):
            raise _fail("TerminateJobObject")

    def terminate_child(self, child: Child) -> None:
        if not self.k.TerminateProcess(child.process, 1):
            raise _fail("TerminateProcess")

    def close_thread(self, child: Child) -> None:
        self.k.CloseHandle(child.thread)

    def close_child(self, child: Child) -> None:
        self.k.CloseHandle(child.process)

    def close_job(self, job: int) -> None:
        self.k.CloseHandle(job)
