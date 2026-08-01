import base64
import ctypes
import os
from ctypes import wintypes


PREFIX = "dpapi:v1:"


def is_sensitive_key(key: str) -> bool:
    value = str(key or "").lower()
    return any(part in value for part in ("api_key", "token", "password", "secret"))


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob(data: bytes):
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


def _protect_windows(value: str) -> str:
    source, source_buffer = _blob(value.encode("utf-8"))
    output = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    if not crypt32.CryptProtectData(ctypes.byref(source), "ARKEA AI", None, None, None, 0, ctypes.byref(output)):
        raise ctypes.WinError()
    try:
        encrypted = ctypes.string_at(output.pbData, output.cbData)
        return PREFIX + base64.b64encode(encrypted).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)


def _unprotect_windows(value: str) -> str:
    source, source_buffer = _blob(base64.b64decode(value[len(PREFIX):]))
    output = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    if not crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)


def protect_secret(value: str) -> str:
    text = str(value or "")
    if not text or text.startswith(PREFIX):
        return text
    if os.name == "nt":
        return _protect_windows(text)
    return text


def unprotect_secret(value: str) -> str:
    text = str(value or "")
    if not text.startswith(PREFIX):
        return text
    if os.name != "nt":
        return ""
    try:
        return _unprotect_windows(text)
    except Exception:
        return ""
