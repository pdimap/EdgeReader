"""EdgeReader 2.0 beta — Windows 10 desktop interface."""
import queue
import threading
import tkinter as tk
from tkinter import ttk

import keyboard

from reader import Speaker, VOICES, choose_voice
from selection import selected_text, foreground
import json
import os
from pathlib import Path


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("EdgeReader 2.0 Beta")
        self.root.geometry("490x480")
        self.request_id = 0
        self.selection_lock = threading.Lock()
        self.settings_path = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "EdgeReader" / "settings.json"
        self.root.resizable(False, False)
        self.events = queue.Queue()
        self.speaker = Speaker(lambda msg: self.events.put(("status", msg)))
        self.voice = tk.StringVar(value="Автоматически")
        self.speed = tk.DoubleVar(value=1.0)
        self.fallback = tk.BooleanVar(value=True)
        try:
            settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
            if settings.get("voice") in ["Автоматически", *VOICES]:
                self.voice.set(settings["voice"])
            self.speed.set(max(.5, min(2., float(settings.get("speed", 1)))))
        except (OSError, ValueError, TypeError):
            pass
        self.status = tk.StringVar(value="Выделите текст и нажмите Ctrl+Alt+X")

        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="EdgeReader 2.0", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Выделенный текст → горячая клавиша → озвучивание", foreground="#555").pack(anchor="w", pady=(0, 15))
        ttk.Label(frame, text="Голос").pack(anchor="w")
        ttk.Combobox(frame, textvariable=self.voice, state="readonly", values=["Автоматически", *VOICES], width=41).pack(fill="x", pady=(3, 10))
        self.speed_label = ttk.Label(frame, text="Скорость: 1.0×")
        self.speed_label.pack(anchor="w")
        ttk.Scale(frame, from_=0.5, to=2.0, variable=self.speed,
                  command=lambda val: self.speed_label.configure(text=f"Скорость: {float(val):.1f}×")).pack(fill="x", pady=(2, 10))
        ttk.Checkbutton(frame, variable=self.fallback,
                        text="Если прямой доступ недоступен — автоматически Ctrl+C").pack(anchor="w", pady=(0, 12))

        actions = ttk.Frame(frame)
        actions.pack(fill="x")
        ttk.Label(actions, text="Читать: Ctrl+Alt+X").pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(actions, text="Пауза", command=self.speaker.toggle_pause).pack(side="left", padx=4)
        ttk.Button(actions, text="Стоп", command=lambda: self.events.put(("stop", None))).pack(side="left", padx=(4, 0))

        ttk.Label(frame, text="Пауза: Ctrl+Alt+P     Стоп: Ctrl+Alt+Z", foreground="#666").pack(anchor="w", pady=(13, 5))
        ttk.Label(frame, textvariable=self.status, wraplength=405, foreground="#245A93").pack(anchor="w")
        ttk.Button(frame, text="Проверить звук", command=self.test_sound).pack(anchor="w", pady=8)
        ttk.Button(frame, text="Диагностика через 3 секунды", command=self.diagnose).pack(anchor="w")
        ttk.Label(frame, text="Выделенный текст отправляется в онлайн-сервис Microsoft.\nДиагностика: нажмите кнопку и выделите текст в другом окне.", wraplength=450).pack(anchor="w", pady=8)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self.pump)

    def test_sound(self):
        self.request_id += 1
        text = "Проверка звука. EdgeReader готов к чтению."
        self.speaker.speak(text, choose_voice(text, self.voice.get()), self.speed.get())

    def diagnose(self):
        self.status.set("За 3 секунды переключитесь в нужное окно и выделите текст")
        self.root.after(3000, lambda: self.read(foreground(), diagnostic=True))

    def read(self, target=None, diagnostic=False):
        self.request_id += 1
        request = self.request_id
        self.speaker.stop()
        self.status.set("Получаю выделенный текст…")
        voice_mode = self.voice.get()
        speed = self.speed.get()
        fallback = self.fallback.get()

        def worker():
            try:
                with self.selection_lock:
                    if request != self.request_id:
                        return
                    text = selected_text(fallback, target)
                if request != self.request_id:
                    return
                if diagnostic:
                    self.events.put(("status", f"Диагностика: получено {len(text)} символов"))
                    return
                if not text:
                    self.events.put(("status", "Выделенный текст не найден. Проверьте выделение и горячие клавиши."))
                    return
                self.events.put(("speak", (request, text, choose_voice(text, voice_mode), speed)))
            except Exception as exc:
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
                    self.read(payload)
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
            keyboard.add_hotkey("ctrl+alt+x", lambda: self.events.put(("read", foreground())))
            keyboard.add_hotkey("ctrl+alt+p", self.speaker.toggle_pause)
            keyboard.add_hotkey("ctrl+alt+z", lambda: self.events.put(("stop", None)))
        except Exception as exc:
            self.status.set(f"Горячие клавиши недоступны: {exc}")
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
