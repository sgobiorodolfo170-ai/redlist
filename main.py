import ctypes
import datetime
import os
import sys
import traceback

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.main_window import MainWindow
from src.settings import Settings

ERROR_LOG = "报错日志.md"


def _get_log_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))


def write_error_log(exc_type, exc_value, exc_traceback):
    try:
        log_path = os.path.join(_get_log_dir(), ERROR_LOG)
        lines = [
            "# 报错日志",
            "",
            f"- **时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **错误类型**: {exc_type.__name__}",
            f"- **错误信息**: {exc_value}",
            "",
            "## 堆栈跟踪",
            "",
            "```",
        ]
        lines.extend(traceback.format_exception(exc_type, exc_value, exc_traceback))
        lines.append("```")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception:
        pass


def _check_single_instance():
    try:
        kernel32 = ctypes.windll.kernel32
        mutex = kernel32.CreateMutexW(None, False, "Global\\RedList-App-Mutex")
        if mutex and ctypes.GetLastError() == 183:
            kernel32.CloseHandle(mutex)
            return False
        _check_single_instance.mutex = mutex
        return True
    except Exception:
        return True


def main():
    if not _check_single_instance():
        return

    try:
        app = QApplication(sys.argv)
    except Exception as e:
        write_error_log(type(e), e, e.__traceback__)
        return

    app.setApplicationName("RedList")
    app.setOrganizationName("RedList")
    app.setQuitOnLastWindowClosed(False)

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RedList.RedList.1.0")
    except Exception:
        pass

    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))
    icon_path = os.path.join(base_path, 'app-icons', 'RedList.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    def exception_hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        write_error_log(exc_type, exc_value, exc_traceback)
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"Error: {error_msg}")
        QMessageBox.critical(None, "错误", f"程序发生错误，详情请查看 {ERROR_LOG}")

    sys.excepthook = exception_hook

    try:
        settings = Settings()
        window = MainWindow(settings)
        window.show()
    except Exception as e:
        write_error_log(type(e), e, e.__traceback__)
        QMessageBox.critical(None, "启动失败", f"程序启动失败，详情请查看 {ERROR_LOG}")
        return

    try:
        sys.exit(app.exec())
    except Exception as e:
        write_error_log(type(e), e, e.__traceback__)


if __name__ == "__main__":
    main()
