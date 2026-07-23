import os
import sys
import types

frozen = getattr(sys, 'frozen', False)
if frozen:
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        paddle_lib_dir = os.path.join(meipass, "paddle", "libs")
        if os.path.isdir(paddle_lib_dir):
            current_path = os.environ.get("PATH", "")
            os.environ["PATH"] = paddle_lib_dir + os.pathsep + current_path

        paddleocr_dir = os.path.join(meipass, "paddleocr")
        if os.path.isdir(paddleocr_dir):
            sys.path.insert(0, paddleocr_dir)
        else:
            alt = os.path.join(meipass, "_internal", "paddleocr")
            if os.path.isdir(alt):
                sys.path.insert(0, alt)

class _StubModule(types.ModuleType):
    def __getattr__(self, name):
        child = _StubModule(f"{self.__name__}.{name}")
        child.__package__ = child.__name__
        setattr(self, name, child)
        return child
    def __call__(self, *args, **kwargs):
        return self

_stub_prefixes = [
    "imgaug", "albumentations",
    "pdf2docx", "editdistance", "premailer",
    "wandb", "fasttext", "paddleclas", "paddlenlp", "tablepyxl",
]

class _StubLoader:
    def find_spec(self, fullname, path, target=None):
        for prefix in _stub_prefixes:
            if fullname == prefix or fullname.startswith(prefix + "."):
                mod = _StubModule(fullname)
                mod.__package__ = fullname.rpartition(".")[0] if "." in fullname else fullname
                return importlib.machinery.ModuleSpec(fullname, self, is_package=False)
        return None
    def create_module(self, spec):
        mod = _StubModule(spec.name)
        mod.__package__ = spec.name.rpartition(".")[0] if "." in spec.name else spec.name
        sys.modules[spec.name] = mod
        return mod
    def exec_module(self, module):
        pass

import importlib.machinery
sys.meta_path.insert(0, _StubLoader())
