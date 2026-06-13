import os
import sys

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    paddle_libs = os.path.join(base_path, 'paddle', 'libs')
    if os.path.isdir(paddle_libs):
        os.environ['path'] = paddle_libs + ';' + os.environ.get('path', '')
        try:
            os.add_dll_directory(paddle_libs)
        except Exception:
            pass
