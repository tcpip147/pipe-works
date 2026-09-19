import ctypes
import hashlib
from ctypes import wintypes

ERROR_ALREADY_EXISTS = 183

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateMutexW.argtypes = [
    ctypes.c_void_p,
    wintypes.BOOL,
    wintypes.LPCWSTR,
]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL


class DuplicateProcessError(Exception):
    pass


def acquire_process_mutex(process_id: str) -> wintypes.HANDLE:
    process_key = hashlib.sha256(process_id.encode("utf-8")).hexdigest()
    mutex_name = f"Local\\pipe-works-stream-{process_key}"

    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())

    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(mutex)
        raise DuplicateProcessError(f"이미 실행 중인 프로세스입니다: {process_id}")

    return mutex
