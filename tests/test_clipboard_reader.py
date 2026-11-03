import importlib.util
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

class ClipboardTests(unittest.TestCase):
    def setUp(self):
        self.cb = MagicMock()
        self.con = MagicMock(CF_UNICODETEXT=13)
        self.modules = patch.dict(sys.modules, win32clipboard=self.cb, win32con=self.con)
        self.modules.start()
        spec = importlib.util.spec_from_file_location('clipboard_test', pathlib.Path(__file__).resolve().parents[1] / 'clipboard_reader.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def tearDown(self):
        self.modules.stop()

    def test_text_with_rich_formats_is_read_without_mutation(self):
        self.cb.GetClipboardData.return_value = '  Українська и русский\nHello  '
        self.assertEqual(self.module.copied_text(), 'Українська и русский\nHello')
        self.cb.GetClipboardData.assert_called_once_with(13)
        self.cb.CloseClipboard.assert_called_once()
        self.cb.EmptyClipboard.assert_not_called()
        self.cb.SetClipboardData.assert_not_called()
        self.cb.EnumClipboardFormats.assert_not_called()

    def test_image_only_rejected(self):
        self.cb.IsClipboardFormatAvailable.return_value = False
        with self.assertRaisesRegex(RuntimeError, 'нет текста'):
            self.module.copied_text()
        self.cb.CloseClipboard.assert_called_once()

    def test_empty_rejected(self):
        self.cb.GetClipboardData.return_value = ' \n '
        with self.assertRaisesRegex(RuntimeError, 'пуст'):
            self.module.copied_text()

    def test_locked_clipboard_retries(self):
        self.cb.OpenClipboard.side_effect = [OSError(), None]
        self.cb.GetClipboardData.return_value = 'text'
        with patch.object(self.module.time, 'sleep'):
            self.assertEqual(self.module.copied_text(), 'text')
        self.assertEqual(self.cb.OpenClipboard.call_count, 2)

    def test_permanently_locked_reports_error(self):
        self.cb.OpenClipboard.side_effect = OSError()
        with patch.object(self.module.time, 'sleep'), self.assertRaisesRegex(RuntimeError, 'занят'):
            self.module.copied_text()
        self.cb.CloseClipboard.assert_not_called()

    def test_read_error_releases_clipboard(self):
        self.cb.GetClipboardData.side_effect = OSError()
        with self.assertRaises(OSError):
            self.module.copied_text()
        self.cb.CloseClipboard.assert_called_once()
