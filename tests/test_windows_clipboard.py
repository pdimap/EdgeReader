"""Real Windows clipboard round trip on the disposable CI runner."""
import sys
import unittest

@unittest.skipUnless(sys.platform == 'win32', 'Windows integration')
class WindowsClipboardTests(unittest.TestCase):
    def test_unicode_with_html_remains_intact(self):
        import win32clipboard as cb
        import win32con
        from clipboard_reader import copied_text
        text = 'Проверка Українська English\nВторая строка'
        html_id = cb.RegisterClipboardFormat('HTML Format')
        rich = b'<html><body>test</body></html>\0'
        cb.OpenClipboard()
        try:
            cb.EmptyClipboard()
            cb.SetClipboardData(win32con.CF_UNICODETEXT, text)
            cb.SetClipboardData(html_id, rich)
            before = cb.GetClipboardSequenceNumber()
        finally:
            cb.CloseClipboard()
        try:
            self.assertEqual(copied_text(), text)
            cb.OpenClipboard()
            try:
                self.assertEqual(cb.GetClipboardSequenceNumber(), before)
                self.assertEqual(cb.GetClipboardData(html_id), rich)
                self.assertEqual(cb.GetClipboardData(win32con.CF_UNICODETEXT), text)
            finally:
                cb.CloseClipboard()
        finally:
            cb.OpenClipboard()
            cb.EmptyClipboard()
            cb.CloseClipboard()

    def test_hotkey_routes_copied_text_to_speaker(self):
        import time
        import keyboard
        import win32clipboard as cb
        import win32con
        from unittest.mock import patch
        from edge_reader import App
        with patch('edge_reader.Speaker') as speaker_class:
            app = App()
            app.root.withdraw()
            cb.OpenClipboard()
            try:
                cb.EmptyClipboard()
                cb.SetClipboardData(win32con.CF_UNICODETEXT, 'Проверка горячей клавиши')
            finally:
                cb.CloseClipboard()
            result = []
            def trigger():
                keyboard.send('ctrl+alt+x')
                app.root.after(100, check)
            deadline = time.monotonic() + 8
            def check():
                if speaker_class.return_value.speak.called:
                    result.append(speaker_class.return_value.speak.call_args.args[0])
                    app.close()
                elif time.monotonic() > deadline:
                    app.close()
                else:
                    app.root.after(100, check)
            app.root.after(300, trigger)
            try:
                app.run()
                self.assertEqual(result, ['Проверка горячей клавиши'])
            finally:
                keyboard.unhook_all_hotkeys()
