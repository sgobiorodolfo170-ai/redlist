import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.llm_chat.conversation_manager import ConversationManager


class TestConversationManagerCreation:
    def test_create_conversation(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "test-model", "api_key": "abc123", "api_url": "https://api.test.com"}
        conv_id = cm.create_conversation(model_config)

        assert isinstance(conv_id, str)
        assert len(conv_id) > 0

        data = cm.get_conversation(conv_id)
        assert data is not None
        assert data["id"] == conv_id
        assert data["title"] == "新会话"
        assert data["model"]["name"] == "test-model"
        assert data["messages"] == []

        path = cm._path(conv_id)
        assert path.exists()

    def test_create_conversation_has_timestamps(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        data = cm.get_conversation(conv_id)
        assert "created_at" in data
        assert "updated_at" in data
        assert "20" in data["created_at"]

    def test_create_conversation_caches_entry(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        assert conv_id in cm._conv_cache
        assert cm._list_cache is None

    def test_create_conversation_overwrites_existing(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        time.sleep(0.05)
        cm.create_conversation(model_config)
        data = cm.get_conversation(conv_id)
        assert data is not None
        assert data["title"] == "新会话"


class TestConversationManagerGet:
    def test_get_existing(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        data = cm.get_conversation(conv_id)
        assert data["id"] == conv_id

    def test_get_nonexistent(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        data = cm.get_conversation("9999999999999")
        assert data is None

    def test_get_corrupt_json(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        conv_id = str(int(time.time() * 1000))
        path = cm._path(conv_id)
        path.write_text("not valid json {{{", encoding="utf-8")

        data = cm.get_conversation(conv_id)
        assert data is None

    def test_get_stores_in_cache(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        cm._conv_cache.clear()
        data = cm.get_conversation(conv_id)
        assert data is not None
        assert conv_id in cm._conv_cache

    def test_get_respects_cache_max_size(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)

        for i in range(60):
            model_config = {"name": f"m{i}", "api_key": "k", "api_url": "https://x.com"}
            cid = cm.create_conversation(model_config)
            cm.get_conversation(cid)

        assert len(cm._conv_cache) <= cm._CACHE_MAX_SIZE


class TestConversationManagerSaveMessage:
    def test_save_message_updates_title_from_first_user(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        messages = [
            {"role": "user", "content": "你好，请问这是什么？"},
            {"role": "assistant", "content": "这是一张图片。"},
        ]
        cm.save_message(conv_id, messages)
        data = cm.get_conversation(conv_id)
        assert data["title"] == "你好，请问这是什么？"
        assert data["messages"] == messages

    def test_save_message_truncates_long_title(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        long_text = "a" * 100
        messages = [{"role": "user", "content": long_text}]
        cm.save_message(conv_id, messages)
        data = cm.get_conversation(conv_id)
        assert len(data["title"]) == 33

    def test_save_message_multimodal_content(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "看图说话"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
                ],
            },
            {"role": "assistant", "content": "这是一张风景照。"},
        ]
        cm.save_message(conv_id, messages)
        data = cm.get_conversation(conv_id)
        assert data["title"] == "看图说话"

    def test_save_message_skips_non_text_parts(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "data:..."}},
                ],
            },
            {"role": "assistant", "content": "回复。"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "第二句用户消息"},
                ],
            },
        ]
        cm.save_message(conv_id, messages)
        data = cm.get_conversation(conv_id)
        assert data["title"] == "第二句用户消息"

    def test_save_message_no_messages_keeps_title(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        cm.save_message(conv_id, [])
        data = cm.get_conversation(conv_id)
        assert data["title"] == "新会话"

    def test_save_message_updates_updated_at(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        initial_data = cm.get_conversation(conv_id)
        old_updated = initial_data["updated_at"]

        messages = [{"role": "user", "content": "test"}]
        with patch("src.llm_chat.conversation_manager.time") as mock_time:
            def fake_strftime(fmt, t_tuple=None):
                return f"formatted-{int(t_tuple or 0)}"
            mock_time.time.side_effect = [1000000.0, 2000000.0]
            mock_time.strftime.side_effect = fake_strftime
            cm.save_message(conv_id, messages)
        data = cm.get_conversation(conv_id)
        assert data["updated_at"] != old_updated

    def test_save_message_conv_not_found(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        cm.save_message("nonexistent_id", [{"role": "user", "content": "test"}])


class TestConversationManagerRename:
    def test_rename(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        cm.rename_conversation(conv_id, "新标题")
        data = cm.get_conversation(conv_id)
        assert data["title"] == "新标题"

    def test_rename_nonexistent(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        cm.rename_conversation("nonexistent", "新标题")

    def test_rename_invalidates_cache(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        cm.get_conversation(conv_id)
        cm.rename_conversation(conv_id, "新标题")
        data = cm.get_conversation(conv_id)
        assert data["title"] == "新标题"


class TestConversationManagerDelete:
    def test_delete(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        cm.delete_conversation(conv_id)
        assert cm.get_conversation(conv_id) is None
        assert not cm._path(conv_id).exists()

    def test_delete_nonexistent(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        cm.delete_conversation("nonexistent_id")


class TestConversationManagerList:
    def test_list_empty(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        result = cm.list_conversations()
        assert result == []

    def test_list_conversations(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)

        for i in range(3):
            mc = {"name": f"m{i}", "api_key": "k", "api_url": "https://x.com"}
            cid = cm.create_conversation(mc)
            cm.save_message(cid, [{"role": "user", "content": f"msg{i}"}])
            if i < 2:
                time.sleep(0.05)

        result = cm.list_conversations()
        assert len(result) == 3
        for item in result:
            assert "id" in item
            assert "title" in item
            assert "message_count" in item
            assert item["message_count"] == 1

    def test_list_ignores_non_json_files(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        cm.create_conversation(model_config)

        junk = cm.conversations_dir / "junk.txt"
        junk.write_text("not a conversation", encoding="utf-8")

        result = cm.list_conversations()
        assert len(result) == 1

    def test_list_uses_cache(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        cm.create_conversation(model_config)

        r1 = cm.list_conversations()
        r2 = cm.list_conversations()
        assert r1 is r2

    def test_list_invalidates_on_delete(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        r1 = cm.list_conversations()
        assert len(r1) == 1

        cm.delete_conversation(conv_id)
        r2 = cm.list_conversations()
        assert len(r2) == 0

    def test_list_skips_corrupt_json(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        cm.create_conversation(model_config)

        corrupt_path = cm.conversations_dir / "corrupt.json"
        corrupt_path.write_text("{invalid json", encoding="utf-8")

        result = cm.list_conversations()
        assert len(result) == 1

    def test_list_shows_model_name(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "gpt-4o", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        result = cm.list_conversations()
        assert result[0]["model_name"] == "gpt-4o"

    def test_list_empty_model_name(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        cm.create_conversation({})

        result = cm.list_conversations()
        assert result[0]["model_name"] == ""


class TestConversationManagerInvalidate:
    def test_invalidate_single(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        conv_id = cm.create_conversation(model_config)

        cm._conv_cache[conv_id] = {"title": "old"}
        cm._invalidate(conv_id)
        assert conv_id not in cm._conv_cache

    def test_invalidate_all(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        model_config = {"name": "m", "api_key": "k", "api_url": "https://x.com"}
        cm.create_conversation(model_config)
        cm._conv_cache["other"] = {}

        cm._invalidate()
        assert len(cm._conv_cache) == 0

    def test_invalidate_clears_list_cache(self, temp_dir):
        settings = MagicMock()
        settings.get.return_value = str(temp_dir)
        cm = ConversationManager(settings)
        cm._list_cache = [{"id": "1"}]
        cm._invalidate()
        assert cm._list_cache is None
