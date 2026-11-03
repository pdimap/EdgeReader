import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import patch


class ReaderTests(unittest.TestCase):
    def setUp(self):
        deps = {name: types.ModuleType(name) for name in ('edge_tts', 'miniaudio', 'numpy', 'sounddevice')}
        self.patch = patch.dict(sys.modules, deps)
        self.patch.start()
        spec = importlib.util.spec_from_file_location('reader_test', pathlib.Path(__file__).resolve().parents[1] / 'reader.py')
        self.reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.reader)

    def tearDown(self):
        self.patch.stop()

    def test_chunking_preserves_words(self):
        text = 'Тест предложения. ' * 1000
        pieces = list(self.reader.chunks(text))
        self.assertTrue(all(0 < len(p) <= 450 for p in pieces))
        self.assertEqual(' '.join(pieces), ' '.join(text.split()))

    def test_unbroken_long_text(self):
        pieces = list(self.reader.chunks('x' * 1001))
        self.assertEqual(''.join(pieces), 'x' * 1001)
        self.assertTrue(all(len(p) <= 450 for p in pieces))

    def test_language_and_override(self):
        self.assertIn('uk-UA', self.reader.choose_voice('Українська', 'Автоматически'))
        self.assertIn('ru-RU', self.reader.choose_voice('Пример', 'Автоматически'))
        self.assertIn('en-US', self.reader.choose_voice('Hello', 'Автоматически'))
        self.assertIn('uk-UA', self.reader.choose_voice('Hello', 'Українська — жіночий'))

    def test_stop_releases_pause_and_cancels_session(self):
        speaker = self.reader.Speaker(lambda _: None)
        speaker._pause.set()
        speaker.stop()
        self.assertTrue(speaker._stop.is_set())
        self.assertFalse(speaker._pause.is_set())
