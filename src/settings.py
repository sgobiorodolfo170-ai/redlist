import json
import os
import sys
from pathlib import Path
from typing import Any

from src.utils.debounce import Debouncer
from src.utils.logger import get_logger

logger = get_logger("Settings")


def set_auto_start(enabled: bool) -> bool:
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "RedList"

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
        if enabled:
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                exe_path = os.path.abspath(sys.argv[0])
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except ImportError:
        logger.warning("winreg not available (not Windows?)")
        return False
    except PermissionError as e:
        logger.error(f"Permission denied when setting auto start: {e}")
        return False
    except Exception as e:
        logger.exception(f"Failed to set auto start: {e}")
        return False


def is_auto_start_enabled() -> bool:
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "RedList"

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, app_name)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except ImportError:
        return False
    except Exception as e:
        logger.debug(f"Failed to check auto start: {e}")
        return False


class Settings:
    DEFAULT_SETTINGS = {
        "dock_sensitivity": 5,
        "screenshot_path": "",
        "data_path": "",
        "play_sound": True,
        "auto_start": False,
        "theme": "light",
        "alarm_sound": "alert-sound-on-mobile-phone.mp3",
        "translate_provider": "baidu_llm",
        "baidu_app_id": "",
        "baidu_app_key": "",
        "tencent_secret_id": "",
        "tencent_secret_key": "",
        "deepl_api_key": "",
        "translate_target_lang": "zh"
    }

    SAVE_DELAY_MS = 500

    def __init__(self):
        self.app_data_dir = Path(os.environ.get('APPDATA', '')) / 'RedList'
        self.app_data_dir.mkdir(exist_ok=True)
        self.settings_file = self.app_data_dir / 'settings.json'
        self.settings = self.load_settings()
        self._save_debouncer = Debouncer(delay_ms=self.SAVE_DELAY_MS)
        self._dirty = False

    def load_settings(self) -> dict:
        if self.settings_file.exists():
            try:
                with open(self.settings_file, encoding='utf-8') as f:
                    data = json.load(f)
                    settings = self.DEFAULT_SETTINGS.copy()
                    settings.update(data)
                    return settings
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in settings file: {e}")
            except PermissionError as e:
                logger.error(f"Permission denied reading settings: {e}")
            except Exception as e:
                logger.exception(f"Failed to load settings: {e}")
        return self.DEFAULT_SETTINGS.copy()

    def save(self) -> None:
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            self._dirty = False
        except PermissionError as e:
            logger.error(f"Permission denied saving settings: {e}")
        except Exception as e:
            logger.exception(f"Failed to save settings: {e}")

    def _schedule_save(self) -> None:
        self._dirty = True
        self._save_debouncer.call(self.save)

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any, immediate: bool = False) -> None:
        if self.settings.get(key) == value:
            return

        self.settings[key] = value

        if immediate:
            self.save()
        else:
            self._schedule_save()

    def flush(self) -> None:
        if self._dirty:
            self._save_debouncer.flush()

    def get_screenshot_path(self) -> str:
        path = self.settings.get('screenshot_path', '')
        if not path:
            path = os.path.join(os.environ.get('USERPROFILE', ''), 'Pictures', 'Screenshots')
        return path

    def get_data_path(self) -> str:
        path = self.settings.get('data_path', '')
        if not path:
            path = str(self.app_data_dir)
        return path

    def get_tasks_path(self) -> str:
        path = self.settings.get('data_path', '')
        if not path:
            path = str(self.app_data_dir)
        return os.path.join(path, 'tasks')

    def get_notes_path(self) -> str:
        path = self.settings.get('data_path', '')
        if not path:
            path = str(self.app_data_dir)
        return os.path.join(path, 'notes')

    def get_alarm_sound(self) -> str:
        return self.settings.get('alarm_sound', 'alert-sound-on-mobile-phone.mp3')

    def get_sounds_dir(self) -> str:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, 'resources', 'sounds')

    def get_alarm_sound_path(self) -> str:
        sound_file = self.get_alarm_sound()
        sounds_dir = self.get_sounds_dir()
        return os.path.join(sounds_dir, sound_file)
