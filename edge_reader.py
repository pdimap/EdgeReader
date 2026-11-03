"""EdgeReader 2.0 beta — Windows 10 desktop interface."""
import queue
import threading
import tkinter as tk
from tkinter import ttk

import keyboard

from reader import Speaker, VOICES, choose_voice
from clipboard_reader import copied_text
import json
import os
from pathlib import Path


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("EdgeReader 2.0.2")
        self.root.geometry("490x520")
        self.request_id = 0
        self.selection_lock = threading.Lock()
        self.settings_path = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "EdgeReader" / "settings.json"
        self.root.resizable(False, False)
        self.events = queue.Queue()
        self.speaker = Speaker(lambda msg: self.events.put(("status", msg)))
        self.voice = tk.StringVar(value="Автоматически")
        self.speed = tk.DoubleVar(value=1.0)
        try:
            settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
            if settings.get("voice") in ["Автоматически", *VOICES]:
                self.voice.set(settings["voice"])
            self.speed.set(max(.5, min(2., float(settings.get("speed", 1)))))
        except (OSError, ValueError, TypeError):
            pass
        self.status = tk.StringVar(value="Скопируйте текст Ctrl+C, затем нажмите Ctrl+Alt+X")

        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="EdgeReader 2.0.2", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Выделите текст → Ctrl+C → Ctrl+Alt+X", foreground="#555").pack(anchor="w", pady=(0, 15))
        ttk.Label(frame, text="Голос").pack(anchor="w")
        ttk.Combobox(frame, textvariable=self.voice, state="readonly", values=["Автоматически", *VOICES], width=41).pack(fill="x", pady=(3, 10))
        self.speed_label = ttk.Label(frame, text="Скорость: 1.0×")
        self.speed_label.pack(anchor="w")
        ttk.Scale(frame, from_=0.5, to=2.0, variable=self.speed,
                  command=lambda val: self.speed_label.configure(text=f"Скорость: {float(val):.1f}×")).pack(fill="x", pady=(2, 10))

        actions = ttk.Frame(frame)
        actions.pack(fill="x")
        ttk.Label(actions, text="Читать буфер: Ctrl+Alt+X").pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(actions, text="Пауза", command=self.speaker.toggle_pause).pack(side="left", padx=4)
        ttk.Button(actions, text="Стоп", command=lambda: self.events.put(("stop", None))).pack(side="left", padx=(4, 0))

        ttk.Label(frame, text="Пауза: Ctrl+Alt+P     Стоп: Ctrl+Alt+Z", foreground="#666").pack(anchor="w", pady=(13, 5))
        ttk.Label(frame, textvariable=self.status, wraplength=405, foreground="#245A93").pack(anchor="w")
        ttk.Button(frame, text="Прочитать буфер", command=self.read).pack(anchor="w", pady=4)
        ttk.Button(frame, text="Проверить звук", command=self.test_sound).pack(anchor="w", pady=8)
        ttk.Button(frame, text="Проверить текст в буфере", command=self.diagnose).pack(anchor="w")
        ttk.Label(frame, text="Текст из буфера отправляется в онлайн-сервис Microsoft.\nПеред каждым новым текстом нажимайте Ctrl+C.", wraplength=450).pack(anchor="w", pady=8)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self.pump)

    def test_sound(self):
        self.request_id += 1
        text = "Проверка звука. EdgeReader готов к чтению."
        self.speaker.speak(text, choose_voice(text, self.voice.get()), self.speed.get())

    def diagnose(self):
        self.read(diagnostic=True)

    def read(self, diagnostic=False):
        self.request_id += 1
        request = self.request_id
        self.speaker.stop()
        self.status.set("Читаю текст из буфера…")
        voice_mode = self.voice.get()
        speed = self.speed.get()

        def worker():
            try:
                with self.selection_lock:
                    if request != self.request_id:
                        return
                    text = copied_text()
                if request != self.request_id:
                    return
                if diagnostic:
                    self.events.put(("status", f"Диагностика: получено {len(text)} символов"))
                    return
                if not text:
                    self.events.put(("status", "В буфере нет текста. Сначала нажмите Ctrl+C."))
                    return
                self.events.put(("speak", (request, text, choose_voice(text, voice_mode), speed)))
            except Exception as exc:
                if request == self.request_id:
                    self.events.put(("status", f"Не удалось получить текст: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def pump(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "status":
                    self.status.set(payload)
                elif kind == "speak":
                    if payload[0] == self.request_id:
                        self.status.set(f"Текст получен ({len(payload[1])} символов)")
                        self.speaker.speak(*payload[1:])
                elif kind == "stop":
                    self.request_id += 1
                    self.speaker.stop()
                elif kind == "read":
                    self.read()
        except queue.Empty:
            pass
        self.root.after(100, self.pump)

    def close(self):
        self.request_id += 1
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(json.dumps({"voice": self.voice.get(), "speed": self.speed.get()}), encoding="utf-8")
        except OSError:
            pass
        self.speaker.stop()
        keyboard.unhook_all_hotkeys()
        self.root.destroy()

    def run(self):
        try:
            keyboard.add_hotkey("ctrl+alt+x", lambda: self.events.put(("read", None)))
            keyboard.add_hotkey("ctrl+alt+p", self.speaker.toggle_pause)
            keyboard.add_hotkey("ctrl+alt+z", lambda: self.events.put(("stop", None)))
        except Exception as exc:
            self.status.set(f"Горячие клавиши недоступны: {exc}")
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
