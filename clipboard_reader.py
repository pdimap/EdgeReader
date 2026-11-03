"""Read manually copied Unicode text without modifying any clipboard format."""
import time
import win32clipboard as cb
import win32con


def copied_text():
    for attempt in range(20):
        try:
            cb.OpenClipboard()
            break
        except Exception:
            if attempt == 19:
                raise RuntimeError("Буфер занят другой программой. Повторите Ctrl+Alt+X") from None
            time.sleep(.05)
    try:
        if not cb.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            raise RuntimeError("В буфере нет текста. Выделите текст и нажмите Ctrl+C")
        text = cb.GetClipboardData(win32con.CF_UNICODETEXT)
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Буфер пуст. Выделите текст и нажмите Ctrl+C")
        return text.strip()
    finally:
        cb.CloseClipboard()
