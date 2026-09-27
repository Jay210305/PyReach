import importlib

mod = importlib.import_module("os")
eval("print(1)")
exec("x = 2")
getattr(mod, "path")  # noqa: B009
