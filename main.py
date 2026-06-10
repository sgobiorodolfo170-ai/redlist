import sys
import traceback

from PyQt6.QtWidgets import QApplication, QMessageBox

from src.main_window import MainWindow
from src.settings import Settings

# 在打包环境中输出诊断信息
if hasattr(sys, '_MEIPASS'):
    print("=" * 60)
    print("Running in packaged environment")
    print(f"Package path: {sys._MEIPASS}")
    print("=" * 60)


def main():
    # 初始化应用
    app = QApplication(sys.argv)
    app.setApplicationName("RedList")
    app.setOrganizationName("RedList")
    app.setQuitOnLastWindowClosed(False)  # 不自动退出，由主窗口控制

    # 全局异常处理
    def exception_hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"Error: {error_msg}")
        QMessageBox.critical(None, "Error", f"An error occurred:\n{exc_value}")

    sys.excepthook = exception_hook

    # 加载设置
    settings = Settings()

    # 创建并显示主窗口
    window = MainWindow(settings)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
