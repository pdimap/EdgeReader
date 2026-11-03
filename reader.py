"""Speech playback, separate from the desktop interface."""
import asyncio
import re
import threading

import edge_tts
import miniaudio
import numpy as np
import sounddevice as sd

VOICES = {
    "Русский — женский": "ru-RU-SvetlanaNeural",
    "Русский — мужской": "ru-RU-DmitryNeural",
    "Українська — жіночий": "uk-UA-PolinaNeural",
    "Українська — чоловічий": "uk-UA-OstapNeural",
    "English — female": "en-US-AriaNeural",
    "English — male": "en-US-GuyNeural",
}


def choose_voice(text: str, preference: str) -> str:
    if preference != "Автоматически":
        return VOICES[preference]
    if re.search(r"[іїєґІЇЄҐ]", text):
        return VOICES["Українська — жіночий"]
    if re.search(r"[а-яА-ЯёЁ]", text):
        return VOICES["Русский — женский"]
    return VOICES["English — female"]


def chunks(text: str, limit: int = 450):
    text = re.sub(r"\s+", " ", text).strip()
    while text:
        if len(text) <= limit:
            yield text
            break
        cut = max(text.rfind(mark, 0, limit) for mark in (". ", "! ", "? ", "; ", ", "))
        if cut < limit // 3:
            cut = text.rfind(" ", 0, limit)
        if cut < 1:
            cut = limit
        else:
            cut += 1
        yield text[:cut].strip()
        text = text[cut:].strip()


class Speaker:
    def __init__(self, status):
        self.status = status
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._worker = None
        self._lock = threading.Lock()
        self._generation = 0
        self._playback_lock = threading.Lock()

    def speak(self, text: str, voice: str, speed: float):
        with self._lock:
            self._generation += 1
            generation = self._generation
            self._stop.set()
            self._stop = threading.Event()
            self._pause.clear()
            stop_event = self._stop
        self._worker = threading.Thread(target=self._run, args=(text, voice, speed, stop_event, generation), daemon=True)
        self._worker.start()

    def stop(self):
        with self._lock:
            self._generation += 1
            self._stop.set()
            self._pause.clear()
        self.status("Остановлено")

    def toggle_pause(self):
        if not self._worker or not self._worker.is_alive():
            return
        if self._pause.is_set():
            self._pause.clear()
            self.status("Чтение продолжается")
        else:
            self._pause.set()
            self.status("Пауза")

    def _run(self, text, voice, speed, stop_event, generation):
        try:
            self.status("Подключение к озвучиванию…")
            rate = f"{round((speed - 1) * 100):+d}%"
            for part in chunks(text):
                if stop_event.is_set():
                    return
                async def receive():
                    buffer = bytearray()
                    async for packet in edge_tts.Communicate(part, voice, rate=rate).stream():
                        if stop_event.is_set():
                            break
                        if packet["type"] == "audio":
                            buffer.extend(packet["data"])
                    return bytes(buffer)

                async def cancellable_receive():
                    task = asyncio.create_task(receive())
                    try:
                        for _ in range(600):
                            if stop_event.is_set():
                                return b""
                            done, _ = await asyncio.wait({task}, timeout=.1)
                            if done:
                                return task.result()
                        raise TimeoutError("Сервис TTS не ответил за 60 секунд; проверьте интернет")
                    finally:
                        if not task.done():
                            task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
                mp3 = asyncio.run(cancellable_receive())
                if stop_event.is_set():
                    return
                if not mp3:
                    raise RuntimeError("Сервис не вернул аудио")
                decoded = miniaudio.decode(mp3, output_format=miniaudio.SampleFormat.SIGNED16)
                samples = np.frombuffer(decoded.samples, dtype=np.int16)
                if decoded.nchannels > 1:
                    samples = samples.reshape(-1, decoded.nchannels)
                if stop_event.is_set():
                    return
                self.status("Получен звук. Воспроизведение…")
                with self._playback_lock, sd.OutputStream(samplerate=decoded.sample_rate, channels=decoded.nchannels, dtype="int16") as stream:
                    for offset in range(0, len(samples), 1024):
                        if stop_event.is_set():
                            return
                        while self._pause.is_set() and not stop_event.wait(0.05):
                            pass
                        if stop_event.is_set():
                            return
                        stream.write(np.ascontiguousarray(samples[offset:offset + 1024]))
            if not stop_event.is_set() and generation == self._generation:
                self.status("Готово")
        except Exception as exc:
            if not stop_event.is_set() and generation == self._generation:
                self.status(f"Ошибка озвучивания ({type(exc).__name__}). Проверьте интернет и аудиоустройство.")
