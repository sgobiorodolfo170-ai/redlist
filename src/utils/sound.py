import ctypes
import os
import threading


def play_sound(sound_path: str) -> None:
    def _play():
        try:
            winmm = ctypes.windll.winmm
            winmm.mciSendStringW('close all', 0, 0, 0)
            ext = os.path.splitext(sound_path)[1].lower()
            cmd = f'open "{sound_path}" alias sound'
            if ext == '.mid':
                cmd += ' type sequencer'
            winmm.mciSendStringW(cmd, 0, 0, 0)
            winmm.mciSendStringW('play sound wait', 0, 0, 0)
        finally:
            ctypes.windll.winmm.mciSendStringW('close sound', 0, 0, 0)

    threading.Thread(target=_play, daemon=True).start()
