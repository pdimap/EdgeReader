"""Current selection only. Clipboard fallback refuses formats it cannot preserve."""
import ctypes
import time
import threading
import keyboard
import pythoncom
import uiautomation as auto
import win32clipboard as cb
import win32con

_copy_lock = threading.Lock()


def foreground():
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    return user32.GetForegroundWindow()


def check_target(target):
    if target is not None and foreground() != target:
        raise RuntimeError("FOCUS_CHANGED: активное окно изменилось; выделите текст и повторите")


def from_uia(target=None):
    pythoncom.CoInitialize()
    try:
        check_target(target)
        current = auto.GetFocusedControl()
        for _ in range(6):
            if not current:
                break
            if getattr(current, "IsPassword", False) is True:
                raise RuntimeError("PASSWORD: защищённое поле не читается")
            try:
                pattern = current.GetTextPattern()
                if pattern:
                    text = "\n".join(r.GetText(-1) for r in pattern.GetSelection()).strip()
                    check_target(target)
                    if text:
                        return text
            except RuntimeError:
                raise
            except Exception:
                pass
            current = current.GetParentControl()
        return ""
    finally:
        pythoncom.CoUninitialize()


def _formats():
    formats, fmt = [], 0
    while True:
        fmt = cb.EnumClipboardFormats(fmt)
        if not fmt:
            return formats
        formats.append(fmt)


def from_clipboard_fallback(target=None):
    # Conservative policy: never touch rich, delayed, image or private formats.
    # All supported bytes are snapshotted while holding the clipboard lock.
    with _copy_lock:
        for _ in range(100):
            if not any(keyboard.is_pressed(k) for k in ("ctrl", "alt", "shift", "windows")):
                break
            time.sleep(.02)
        else:
            raise RuntimeError("MODIFIERS_HELD: отпустите клавиши и повторите")
        check_target(target)
        seq = ctypes.windll.user32.GetClipboardSequenceNumber
        cb.OpenClipboard()
        try:
            formats = _formats()
            safe = {win32con.CF_TEXT, win32con.CF_UNICODETEXT, win32con.CF_OEMTEXT, win32con.CF_LOCALE}
            if any(f not in safe for f in formats):
                raise RuntimeError("CLIPBOARD_PROTECTED: буфер содержит сложные данные; они сохранены. Прямое чтение недоступно")
            saved = [(f, cb.GetClipboardData(f)) for f in formats]
            before = seq()
        finally:
            cb.CloseClipboard()
        check_target(target)
        keyboard.send("ctrl+c")
        copied_seq = None
        try:
            for _ in range(30):
                time.sleep(.05)
                check_target(target)
                if seq() != before:
                    cb.OpenClipboard()
                    try:
                        # Clipboard owner must belong to the target application.
                        owner = cb.GetClipboardOwner()
                        user32 = ctypes.windll.user32
                        owner_pid, target_pid = ctypes.c_ulong(), ctypes.c_ulong()
                        user32.GetWindowThreadProcessId(ctypes.c_void_p(owner), ctypes.byref(owner_pid))
                        user32.GetWindowThreadProcessId(ctypes.c_void_p(target or foreground()), ctypes.byref(target_pid))
                        if not owner or owner_pid.value != target_pid.value:
                            raise RuntimeError("CLIPBOARD_CHANGED: буфер изменён другим приложением; чтение отменено")
                        copied_seq = seq()
                        return cb.GetClipboardData(win32con.CF_UNICODETEXT).strip() if cb.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT) else ""
                    finally:
                        cb.CloseClipboard()
            return ""
        finally:
            if copied_seq is not None:
                cb.OpenClipboard()
                try:
                    if seq() == copied_seq:
                        cb.EmptyClipboard()
                        for fmt, data in saved:
                            cb.SetClipboardData(fmt, data)
                finally:
                    cb.CloseClipboard()


def selected_text(allow_fallback=True, target=None):
    check_target(target)
    try:
        text = from_uia(target) if target is not None else from_uia()
    except RuntimeError:
        raise
    except Exception:
        text = ""
    if text or not allow_fallback:
        return text
    return from_clipboard_fallback(target) if target is not None else from_clipboard_fallback()
