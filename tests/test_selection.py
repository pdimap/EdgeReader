"""Platform-independent unit tests using mocked Windows APIs.

These do not replace a Windows 10 integration test.
"""
import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


ROOT = pathlib.Path(__file__).resolve().parents[1]


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.modules = {
            name: types.ModuleType(name)
            for name in ("keyboard", "pyperclip", "pythoncom", "uiautomation", "win32clipboard", "win32con")
        }
        self.modules["pythoncom"].CoInitialize = MagicMock()
        self.modules["pythoncom"].CoUninitialize = MagicMock()
        self.modules["win32con"].CF_TEXT = 1
        self.modules["win32con"].CF_UNICODETEXT = 13
        self.modules["win32con"].CF_OEMTEXT = 7
        self.modules["win32con"].CF_LOCALE = 16
        self.mod_patch = patch.dict(sys.modules, self.modules)
        self.mod_patch.start()
        spec = importlib.util.spec_from_file_location("selection_under_test", ROOT / "selection.py")
        self.selection = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.selection)

    def tearDown(self):
        self.mod_patch.stop()

    def test_com_is_initialized_and_released_with_selection(self):
        text_range = MagicMock()
        text_range.GetText.return_value = "Пример текста"
        pattern = MagicMock()
        pattern.GetSelection.return_value = [text_range]
        control = MagicMock()
        control.GetTextPattern.return_value = pattern
        self.modules["uiautomation"].GetFocusedControl = lambda: control
        self.assertEqual(self.selection.from_uia(), "Пример текста")
        self.modules["pythoncom"].CoInitialize.assert_called_once()
        self.modules["pythoncom"].CoUninitialize.assert_called_once()

    def test_com_released_when_focus_provider_throws(self):
        def fail():
            raise RuntimeError("provider failure")
        self.modules["uiautomation"].GetFocusedControl = fail
        with self.assertRaises(RuntimeError):
            self.selection.from_uia()
        self.modules["pythoncom"].CoUninitialize.assert_called_once()

    def test_auto_fallback_when_uia_has_no_selection(self):
        with patch.object(self.selection, "from_uia", return_value=""), \
                patch.object(self.selection, "from_clipboard_fallback", return_value="selected") as fallback:
            self.assertEqual(self.selection.selected_text(), "selected")
            fallback.assert_called_once()

    def test_no_fallback_when_uia_successful(self):
        with patch.object(self.selection, "from_uia", return_value="text"), \
                patch.object(self.selection, "from_clipboard_fallback") as fallback:
            self.assertEqual(self.selection.selected_text(), "text")
            fallback.assert_not_called()

    def test_no_fallback_when_disabled(self):
        with patch.object(self.selection, "from_uia", return_value=""), \
                patch.object(self.selection, "from_clipboard_fallback") as fallback:
            self.assertEqual(self.selection.selected_text(False), "")
            fallback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
