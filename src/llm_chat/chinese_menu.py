from PyQt6.QtCore import Qt


def _setup_chinese_context_menu(widget):
    widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    widget.customContextMenuRequested.connect(lambda pos: _show_chinese_menu(widget, pos))


def _show_chinese_menu(widget, pos):
    menu = widget.createStandardContextMenu()
    translations = {
        "Undo": "撤销",
        "Redo": "重做",
        "Cut": "剪切",
        "Copy": "复制",
        "Paste": "粘贴",
        "Delete": "删除",
        "Select All": "全选",
    }
    for action in menu.actions():
        text = action.text()
        if text in translations:
            action.setText(translations[text])
    menu.exec(widget.mapToGlobal(pos))
