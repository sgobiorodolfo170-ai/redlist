import ctypes
import os


def play_sound(sound_path: str) -> None:
    sound_path = sound_path.replace('\\', '\\\\')
    winmm = ctypes.windll.winmm
    winmm.mciSendStringW('close sound', 0, 0, 0)
    ext = os.path.splitext(sound_path)[1].lower()
    if ext == '.mid':
        winmm.mciSendStringW(f'open "{sound_path}" type sequencer alias sound', 0, 0, 0)
    else:
        winmm.mciSendStringW(f'open "{sound_path}" alias sound', 0, 0, 0)
    winmm.mciSendStringW('play sound', 0, 0, 0)
