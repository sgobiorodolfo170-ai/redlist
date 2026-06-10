# PyInstaller runtime hook for paddleocr
import os

# 设置环境变量避免 paddleocr 输出日志
os.environ['GLOG_minloglevel'] = '2'
os.environ['minloglevel'] = '2'
