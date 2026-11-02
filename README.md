# EdgeReader 2.0 Beta (development checkpoint, fix 2) for Windows 10 (64-bit)

## Fix 2 — not yet released

When Windows UI Automation does not expose the selected text (common with some Chrome/PDF controls), the former build displayed "Выделение не найдено" because clipboard fallback was disabled by default. Fix 2 enables it by default and adds unit tests. This change still needs an actual Windows 10 integration test before release.

Tests executable on development machines: `python -m unittest discover -s tests -v`. Five mock-based tests currently pass. They do not confirm clipboard fidelity or real GUI interoperability.

## Fix 1 (COM initialization)

The screenshot error `[WinError -2147221008] Не был произведен вызов CoInitialize` was caused by calling Windows UI Automation from a background thread without initializing COM. `selection.py` now calls `pythoncom.CoInitialize()` and `pythoncom.CoUninitialize()` on the same worker thread. Clipboard fallback also waits for hotkey keys to be released and refuses to overwrite complex clipboard formats.

You must **rebuild** the EXE using the new project files: the earlier EXE will not update itself.

## What works

- Select text and press **Ctrl+Alt+X**. The app first tries Windows UI Automation (`TextPattern.GetSelection`).
- Voice selection: automatic, Russian, Ukrainian, English; male/female options.
- **Ctrl+Alt+P** pauses/resumes; **Ctrl+Alt+Z** stops playback.
- Speech uses Microsoft's online Edge service and therefore needs internet access.
- Optional clipboard fallback for apps where UI Automation cannot see selection.

## Build on Windows 10

Install Python 3.11 (64-bit), tick **Add Python to PATH**, then double-click `build_windows.bat`.
The resulting program will be `dist\EdgeReader-2.0.exe`; users of that EXE do not need to install Python.

For development without packaging: `pip install -r requirements.txt` and `python edge_reader.py`.

## Beta limitations

- UI Automation works only in applications that expose the selected text; selection access must be tested in Chrome, Word, and individual PDF viewers.
- Clipboard fallback is enabled by default; it uses simulated Ctrl+C and preserves only **plain text**. When non-text or rich formats are detected, it stops with an error instead of overwriting them. The option can be disabled in the UI.
- Audio is sent for online TTS processing. Do not use on sensitive corporate text.
- There is no translation, OCR, system tray integration, offline speech, or installer yet.
- Built-in global hotkeys may conflict with other apps; standard-user Windows sessions only (not secure desktops).
- This beta has not yet been run on Windows; the build and cross-application behavior require real Windows validation.

## Suggested manual test

1. Start EdgeReader, select text in Notepad, press Ctrl+Alt+X.
2. Repeat in Chrome address-page text, Word document body, and a PDF opened in Edge/Acrobat.
3. Verify Pause/Stop; try Russian, Ukrainian, and English with each voice.
4. Test no selection and no internet; verify the app displays an error.
5. Test the optional fallback with a **plain-text-only** clipboard and check that it restores your text.
