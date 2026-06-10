from src.settings import Settings


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
