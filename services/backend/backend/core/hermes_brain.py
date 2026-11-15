import importlib as _il
_m = _il.import_module('app.brain.hermes_brain')
for _k, _v in _m.__dict__.items():
    if not (_k.startswith('__') and _k.endswith('__')):
        globals()[_k] = _v
