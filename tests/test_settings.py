import json
import sys
from unittest.mock import MagicMock, patch

from src.settings import Settings, is_auto_start_enabled, set_auto_start


class TestSetAutoStart:
    def test_enable_success(self):
        mock_winreg = MagicMock()
        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            result = set_auto_start(True)
            assert result
            mock_winreg.OpenKey.assert_called_once()
            mock_winreg.SetValueEx.assert_called_once()

    def test_disable_success(self):
        mock_winreg = MagicMock()
        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            result = set_auto_start(False)
            assert result
            mock_winreg.DeleteValue.assert_called_once()

    def test_disable_file_not_found(self):
        mock_winreg = MagicMock()
        mock_winreg.DeleteValue.side_effect = FileNotFoundError
        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            result = set_auto_start(False)
            assert result

    def test_permission_error_returns_false(self):
        mock_winreg = MagicMock()
        mock_winreg.OpenKey.side_effect = PermissionError("access denied")
        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            result = set_auto_start(True)
            assert not result


class TestIsAutoStartEnabled:
    def test_enabled(self):
        mock_winreg = MagicMock()
        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            assert is_auto_start_enabled()
            mock_winreg.QueryValueEx.assert_called_once()

    def test_not_found(self):
        mock_winreg = MagicMock()
        mock_winreg.QueryValueEx.side_effect = FileNotFoundError
        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            assert not is_auto_start_enabled()



class TestSettings:
    def test_default_values(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings = Settings()
        assert settings.get("theme") == "light"
        assert settings.get("dock_sensitivity") == 5
        assert settings.get("translate_provider") == "baidu_llm"

    def test_set_and_get(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings = Settings()
        settings.set("theme", "dark", immediate=True)
        assert settings.get("theme") == "dark"

    def test_persist_to_disk(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        s1 = Settings()
        s1.set("theme", "dark", immediate=True)
        s2 = Settings()
        assert s2.get("theme") == "dark"

    def test_get_screenshot_path_default(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        monkeypatch.setenv("USERPROFILE", str(temp_dir))
        settings = Settings()
        path = settings.get_screenshot_path()
        assert "Screenshots" in path

    def test_get_screenshot_path_custom(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings = Settings()
        settings.set("screenshot_path", "C:\\custom\\path", immediate=True)
        assert settings.get_screenshot_path() == "C:\\custom\\path"

    def test_get_tasks_path(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings = Settings()
        path = settings.get_tasks_path()
        assert path.endswith("tasks")

    def test_get_notes_path(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings = Settings()
        path = settings.get_notes_path()
        assert path.endswith("notes")

    def test_get_data_path_default(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings = Settings()
        path = settings.get_data_path()
        assert temp_dir.drive in path

    def test_get_data_path_custom(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings = Settings()
        settings.set("data_path", "D:\\data", immediate=True)
        assert settings.get_data_path() == "D:\\data"

    def test_flush_dirty(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings = Settings()
        settings.set("theme", "dark", immediate=False)
        assert settings._dirty
        settings.flush()
        assert not settings._dirty

    def test_load_settings_json_decode_error(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings_file = temp_dir / "RedList" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text("invalid json", encoding="utf-8")
        settings = Settings()
        assert settings.get("theme") == "light"

    def test_load_settings_migration_from_old_fields(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings_file = temp_dir / "RedList" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text(
            json.dumps({"baidu_app_id": "old_id", "baidu_app_key": "old_key"}),
            encoding="utf-8",
        )
        settings = Settings()
        assert settings.get("baidu_nmt_app_id") == "old_id"
        assert settings.get("baidu_nmt_app_key") == "old_key"

    def test_load_settings_migration_does_not_override(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings_file = temp_dir / "RedList" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text(
            json.dumps({
                "baidu_nmt_app_id": "new_id",
                "baidu_nmt_app_key": "new_key",
                "baidu_app_id": "old_id",
                "baidu_app_key": "old_key",
            }),
            encoding="utf-8",
        )
        settings = Settings()
        assert settings.get("baidu_nmt_app_id") == "new_id"

    def test_save_removes_old_fields(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings = Settings()
        settings.settings["baidu_app_id"] = "old"
        settings.settings["baidu_app_key"] = "old"
        settings.save()
        with open(settings.settings_file, encoding="utf-8") as f:
            saved = json.load(f)
        assert "baidu_app_id" not in saved
        assert "baidu_app_key" not in saved

    def test_set_same_value_does_not_save(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings = Settings()
        settings.set("theme", "light")
        assert not settings._dirty

    def test_get_sounds_dir_not_frozen(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings = Settings()
        path = settings.get_sounds_dir()
        assert "resources" in path and "sounds" in path

    def test_get_sounds_dir_frozen(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings = Settings()
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "_MEIPASS", "C:\\frozen", create=True):
            path = settings.get_sounds_dir()
            assert "frozen" in path

    def test_save_permission_error_logged(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings = Settings()
        with patch("builtins.open", side_effect=PermissionError("denied")):
            settings.save()

    def test_save_generic_exception_logged(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings = Settings()
        with patch("builtins.open", side_effect=OSError("disk full")):
            settings.save()

    def test_get_alarm_sound_path(self, monkeypatch, temp_dir):
        monkeypatch.setenv("APPDATA", str(temp_dir))
        settings = Settings()
        path = settings.get_alarm_sound_path()
        assert path.endswith(Settings.DEFAULT_SETTINGS["alarm_sound"])
