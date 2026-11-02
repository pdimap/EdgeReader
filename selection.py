"""Read focused text selection; fall back to simulated copy when enabled."""
import time
import ctypes

import keyboard
import pyperclip
import pythoncom
import uiautomation as auto
import win32clipboard
import win32con


def from_uia():
    # UI Automation uses COM. Every Python worker thread using it MUST
    # initialize and uninitialize COM on that same thread.
    pythoncom.CoInitialize()
    try:
        control = auto.GetFocusedControl()
        if not control:
            return ""
        current = control
        for _ in range(4):
            if not current:
                break
            try:
                pattern = current.GetTextPattern()
                if pattern:
                    selection = pattern.GetSelection()
                    parts = [item.GetText(-1) for item in selection]
                    result = "\n".join(part for part in parts if part).strip()
                    if result:
                        return result
            except Exception:
                pass
            try:
                current = current.GetParentControl()
            except Exception:
                break
        return ""
    finally:
        pythoncom.CoUninitialize()


def from_clipboard_fallback():
    """Use only when explicitly enabled. Preserves plain text, not all rich formats."""
    # Never overwrite non-text clipboard contents (pictures, files, etc.).
    win32clipboard.OpenClipboard()
    try:
        formats = []
        fmt = 0
        try:
            while True:
                fmt = win32clipboard.EnumClipboardFormats(fmt)
                if not fmt:
                    break
                formats.append(fmt)
        except Exception:
            # The empty clipboard has no formats on some Windows builds.
            if formats:
                raise
    finally:
        win32clipboard.CloseClipboard()
    supported_formats = {win32con.CF_TEXT, win32con.CF_UNICODETEXT,
                         win32con.CF_OEMTEXT, win32con.CF_LOCALE}
    if formats and (win32con.CF_UNICODETEXT not in formats or
                    any(fmt not in supported_formats for fmt in formats)):
        raise RuntimeError("В буфере есть изображение или форматированные данные. Сначала скопируйте обычный текст либо используйте прямой режим.")

    old_text = pyperclip.paste()
    # Clear first so an unsupported Ctrl+C cannot return stale content.
    # The hotkey's Ctrl/Alt keys may still be down when callback fires.
    for _ in range(25):
        if not keyboard.is_pressed("alt") and not keyboard.is_pressed("ctrl"):
            break
        time.sleep(0.02)
    else:
        raise RuntimeError("Отпустите Ctrl и Alt и попробуйте снова")
    pyperclip.copy("")
    cleared_seq = ctypes.windll.user32.GetClipboardSequenceNumber()
    keyboard.send("ctrl+c")
    data = ""
    try:
        for _ in range(20):
            time.sleep(0.05)
            if ctypes.windll.user32.GetClipboardSequenceNumber() != cleared_seq:
                data = pyperclip.paste()
                break
    finally:
        # Restore only if no other clipboard write happened meanwhile.
        seq = ctypes.windll.user32.GetClipboardSequenceNumber()
        if seq == cleared_seq or pyperclip.paste() == data:
            pyperclip.copy(old_text)
    return data


def selected_text(allow_fallback=True):
    text = from_uia()
    if text or not allow_fallback:
        return text
    return from_clipboard_fallback()
