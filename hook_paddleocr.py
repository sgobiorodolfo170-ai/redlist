# PyInstaller runtime hook for paddleocr
import os

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['GLOG_minloglevel'] = '2'
os.environ['minloglevel'] = '2'
