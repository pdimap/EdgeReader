"""EdgeReader 2.0 beta — Windows 10 desktop interface."""
import queue
import threading
import tkinter as tk
from tkinter import ttk

import keyboard

from reader import Speaker, VOICES, choose_voice
from selection import selected_text


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("EdgeReader 2.0 Beta")
        self.root.geometry("450x365")
        self.root.resizable(False, False)
        self.events = queue.Queue()
        self.speaker = Speaker(lambda msg: self.events.put(("status", msg)))
        self.voice = tk.StringVar(value="Автоматически")
        self.speed = tk.DoubleVar(value=1.0)
        self.fallback = tk.BooleanVar(value=True)
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
        ttk.Button(actions, text="Стоп", command=self.speaker.stop).pack(side="left", padx=(4, 0))

        ttk.Label(frame, text="Пауза: Ctrl+Alt+P     Стоп: Ctrl+Alt+Z", foreground="#666").pack(anchor="w", pady=(13, 5))
        ttk.Label(frame, textvariable=self.status, wraplength=405, foreground="#245A93").pack(anchor="w")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self.pump)

    def read(self):
        self.status.set("Получаю выделенный текст…")
        voice_mode = self.voice.get()
        speed = self.speed.get()
        fallback = self.fallback.get()

        def worker():
            try:
                text = selected_text(fallback)
                if not text:
                    self.events.put(("status", "Выделенный текст не найден. Проверьте выделение и горячие клавиши."))
                    return
                self.events.put(("speak", (text, choose_voice(text, voice_mode), speed)))
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
                    self.speaker.speak(*payload)
                elif kind == "read":
                    self.read()
        except queue.Empty:
            pass
        self.root.after(100, self.pump)

    def close(self):
        self.speaker.stop()
        keyboard.unhook_all_hotkeys()
        self.root.destroy()

    def run(self):
        try:
            keyboard.add_hotkey("ctrl+alt+x", lambda: self.events.put(("read", None)))
            keyboard.add_hotkey("ctrl+alt+p", self.speaker.toggle_pause)
            keyboard.add_hotkey("ctrl+alt+z", self.speaker.stop)
        except Exception as exc:
            self.status.set(f"Горячие клавиши недоступны: {exc}")
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
