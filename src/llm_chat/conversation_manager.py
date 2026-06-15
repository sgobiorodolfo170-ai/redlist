import json
import os
import time
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger("ConversationManager")


class ConversationManager:
    def __init__(self, settings):
        self.settings = settings
        self.data_dir = Path(settings.get('data_path', '')) or Path(os.environ.get('APPDATA', '')) / 'RedList'
        self.conversations_dir = self.data_dir / 'conversations'
        self.conversations_dir.mkdir(parents=True, exist_ok=True)

    def list_conversations(self):
        convs = []
        for f in sorted(self.conversations_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.suffix == '.json':
                try:
                    with open(f, encoding='utf-8') as fh:
                        data = json.load(fh)
                        convs.append({
                            'id': data.get('id', f.stem),
                            'title': data.get('title', '未命名会话'),
                            'created_at': data.get('created_at', ''),
                            'updated_at': data.get('updated_at', ''),
                            'model_name': data.get('model', {}).get('name', ''),
                            'message_count': len(data.get('messages', [])),
                        })
                except Exception as e:
                    logger.warning(f"Failed to load conversation {f}: {e}")
        return convs

    def create_conversation(self, model_config):
        conv_id = str(int(time.time() * 1000))
        data = {
            'id': conv_id,
            'title': '新会话',
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'model': model_config,
            'messages': [],
        }
        self._save(conv_id, data)
        return conv_id

    def get_conversation(self, conv_id):
        path = self.conversations_dir / f'{conv_id}.json'
        if not path.exists():
            return None
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load conversation {conv_id}: {e}")
            return None

    def save_message(self, conv_id, messages):
        data = self.get_conversation(conv_id)
        if data is None:
            logger.warning(f"Conversation {conv_id} not found for saving")
            return
        data['messages'] = messages
        if messages and len(messages) > 0:
            first_user_msg = None
            for m in messages:
                if m['role'] == 'user':
                    content = m.get('content', '')
                    if isinstance(content, list):
                        for part in content:
                            if part.get('type') == 'text' and part.get('text', '').strip():
                                first_user_msg = part['text']
                                break
                    elif isinstance(content, str) and content.strip():
                        first_user_msg = content
                    if first_user_msg:
                        break
            if first_user_msg:
                data['title'] = first_user_msg[:30] + ('...' if len(first_user_msg) > 30 else '')
        data['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        self._save(conv_id, data)

    def rename_conversation(self, conv_id, title):
        data = self.get_conversation(conv_id)
        if data is None:
            return
        data['title'] = title
        self._save(conv_id, data)

    def delete_conversation(self, conv_id):
        path = self.conversations_dir / f'{conv_id}.json'
        if path.exists():
            path.unlink()
            logger.info(f"Deleted conversation {conv_id}")

    def _save(self, conv_id, data):
        path = self.conversations_dir / f'{conv_id}.json'
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save conversation {conv_id}: {e}")
