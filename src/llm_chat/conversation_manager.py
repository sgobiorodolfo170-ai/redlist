import json
import os
import time
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger("ConversationManager")


class ConversationManager:
    _CACHE_MAX_SIZE = 50

    def __init__(self, settings):
        self.settings = settings
        self.data_dir = Path(settings.get("data_path", "")) or Path(os.environ.get("APPDATA", "")) / "RedList"
        self.conversations_dir = self.data_dir / "conversations"
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        self._conv_cache: dict[str, dict] = {}
        self._list_cache: list[dict] | None = None
        self._list_cache_time = 0
        self._list_cache_ttl = 2.0

    def _invalidate(self, conv_id: str | None = None):
        self._list_cache = None
        self._list_cache_time = 0
        if conv_id:
            self._conv_cache.pop(conv_id, None)
        else:
            self._conv_cache.clear()

    def _path(self, conv_id: str) -> Path:
        return self.conversations_dir / f"{conv_id}.json"

    def list_conversations(self):
        now = time.time()
        if self._list_cache is not None and now - self._list_cache_time < self._list_cache_ttl:
            return self._list_cache

        convs = []
        for f in sorted(self.conversations_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.suffix == ".json":
                conv_id = f.stem
                cached = self._conv_cache.get(conv_id)
                if cached is not None:
                    convs.append(
                        {
                            "id": cached.get("id", conv_id),
                            "title": cached.get("title", "未命名会话"),
                            "created_at": cached.get("created_at", ""),
                            "updated_at": cached.get("updated_at", ""),
                            "model_name": cached.get("model", {}).get("name", ""),
                            "message_count": len(cached.get("messages", [])),
                        }
                    )
                    continue
                try:
                    with open(f, encoding="utf-8") as fh:
                        data = json.load(fh)
                        if len(self._conv_cache) < self._CACHE_MAX_SIZE:
                            self._conv_cache[conv_id] = data
                        convs.append(
                            {
                                "id": data.get("id", conv_id),
                                "title": data.get("title", "未命名会话"),
                                "created_at": data.get("created_at", ""),
                                "updated_at": data.get("updated_at", ""),
                                "model_name": data.get("model", {}).get("name", ""),
                                "message_count": len(data.get("messages", [])),
                            }
                        )
                except Exception as e:
                    logger.warning(f"Failed to load conversation {f}: {e}")

        self._list_cache = convs
        self._list_cache_time = now
        return convs

    def create_conversation(self, model_config):
        conv_id = str(int(time.time() * 1000))
        data = {
            "id": conv_id,
            "title": "新会话",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": model_config,
            "messages": [],
        }
        self._conv_cache[conv_id] = data
        self._save(conv_id, data)
        return conv_id

    def get_conversation(self, conv_id):
        if conv_id in self._conv_cache:
            return self._conv_cache[conv_id]
        path = self._path(conv_id)
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                if len(self._conv_cache) < self._CACHE_MAX_SIZE:
                    self._conv_cache[conv_id] = data
                return data
        except Exception as e:
            logger.error(f"Failed to load conversation {conv_id}: {e}")
            return None

    def save_message(self, conv_id, messages):
        data = self.get_conversation(conv_id)
        if data is None:
            logger.warning(f"Conversation {conv_id} not found for saving")
            return
        data["messages"] = messages
        if messages and len(messages) > 0:
            first_user_msg = None
            for m in messages:
                if m["role"] == "user":
                    content = m.get("content", "")
                    if isinstance(content, list):
                        for part in content:
                            if part.get("type") == "text" and part.get("text", "").strip():
                                first_user_msg = part["text"]
                                break
                    elif isinstance(content, str) and content.strip():
                        first_user_msg = content
                    if first_user_msg:
                        break
            if first_user_msg:
                data["title"] = first_user_msg[:30] + ("..." if len(first_user_msg) > 30 else "")
        data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self._conv_cache[conv_id] = data
        self._save(conv_id, data)

    def rename_conversation(self, conv_id, title):
        data = self.get_conversation(conv_id)
        if data is None:
            return
        data["title"] = title
        self._conv_cache[conv_id] = data
        self._save(conv_id, data)

    def delete_conversation(self, conv_id):
        self._invalidate(conv_id)
        path = self._path(conv_id)
        if path.exists():
            path.unlink()
            logger.info(f"Deleted conversation {conv_id}")

    def _save(self, conv_id, data):
        path = self._path(conv_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save conversation {conv_id}: {e}")
