import sys
import types

_modules = {}

def _make_stub(name):
    parts = name.split('.')
    parent_keys = []
    for i in range(1, len(parts)):
        parent_keys.append('.'.join(parts[:i]))
    for pk in parent_keys:
        if pk not in sys.modules:
            m = types.ModuleType(pk)
            m.__path__ = []
            m.__package__ = pk
            sys.modules[pk] = m

    m = types.ModuleType(name)
    m.__path__ = []
    m.__package__ = name
    m.__file__ = '<stub>'
    sys.modules[name] = m
    return m

_stub_modules = [
    'paddle.utils.cpp_extension',
    'paddle.utils.cpp_extension.extension_utils',
    'paddle.utils.dlpack',
    'paddle.utils.download',
    'paddle.utils.image_util',
    'paddle.utils.layers_utils',
    'paddle.utils.unique_name',
    'paddle.utils.op_version',
]
for n in _stub_modules:
    _make_stub(n)
