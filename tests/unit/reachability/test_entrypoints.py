"""Tests for S3-T7 entry point auto-detection and override merging."""

import ast
import logging

import pytest

from pyreach.ast.builder import ModuleAST
from pyreach.exceptions import ConfigError
from pyreach.reachability.entrypoints import (
    EntryPointDetector,
    detect_or_fail,
    resolve_entry_points,
)


def _module(
    source: str,
    fqn: str = "myapp",
    symbol_table: dict[str, str] | None = None,
) -> ModuleAST:
    tree = ast.parse(source)
    return ModuleAST(
        file_path=f"{fqn}.py",
        module_fqn=fqn,
        tree=tree,
        symbol_table=dict(symbol_table or {}),
        imports={},
    )


def test_detect_main_function() -> None:
    mod = _module("def main():\n    pass\n")
    assert EntryPointDetector([mod]).detect() == ["myapp.main"]


def test_detect_dunder_main_block() -> None:
    mod = _module("def main():\n    pass\n\nif __name__ == '__main__':\n    main()\n")
    entries = EntryPointDetector([mod]).detect()
    assert "myapp.__main__" in entries
    assert "myapp.main" in entries


def test_detect_fastapi_decorator() -> None:
    mod = _module(
        "from fastapi import FastAPI\napp = FastAPI()\n\n"
        "@app.get('/')\ndef read_root():\n    pass\n"
    )
    assert "myapp.read_root" in EntryPointDetector([mod]).detect()


def test_detect_flask_route() -> None:
    mod = _module(
        "from flask import Flask\napp = Flask(__name__)\n\n"
        "@app.route('/')\ndef index():\n    pass\n"
    )
    assert "myapp.index" in EntryPointDetector([mod]).detect()


def test_no_django_autodetect() -> None:
    mod = _module(
        "from django.contrib import admin\n\n@admin.register(Model)\nclass ModelAdmin:\n    pass\n"
    )
    assert EntryPointDetector([mod]).detect() == []


def test_cli_override_union() -> None:
    resolved = resolve_entry_points(["myapp.main"], ["extra.func"], [])
    assert resolved == ["extra.func", "myapp.main"]


def test_colon_normalized() -> None:
    assert resolve_entry_points([], ["pkg.mod:func"], []) == ["pkg.mod.func"]


def test_unknown_override_kept_with_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        resolved = resolve_entry_points([], ["bad.fqn"], [], known_fqns={"myapp.main"})
    assert resolved == ["bad.fqn"]
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_empty_raises() -> None:
    mod = _module("def helper():\n    pass\n")
    with pytest.raises(ConfigError):
        detect_or_fail([mod], [])


def test_asyncio_run_detected() -> None:
    mod = _module("import asyncio\n\ndef main():\n    pass\n\nasyncio.run(main())\n")
    entries = EntryPointDetector([mod]).detect()
    assert "myapp.__main__" in entries
    assert "myapp.main" in entries


def test_allow_empty_does_not_raise() -> None:
    mod = _module("def helper():\n    pass\n")
    assert detect_or_fail([mod], [], allow_empty=True) == []


def test_method_decorator_fqn() -> None:
    mod = _module(
        "class App:\n    @app.get('/users')\n    def list_users(self):\n        pass\n",
        symbol_table={"app": "fastapi.FastAPI"},
    )
    assert "myapp.App.list_users" in EntryPointDetector([mod]).detect()


def test_async_main_detected() -> None:
    mod = _module("async def main():\n    pass\n")
    assert EntryPointDetector([mod]).detect() == ["myapp.main"]


def test_uvicorn_run_detected() -> None:
    mod = _module("import uvicorn\n\nuvicorn.run(app)\n")
    entries = EntryPointDetector([mod]).detect()
    assert "myapp.__main__" in entries
    assert "myapp.app" in entries


def test_runner_attribute_target() -> None:
    mod = _module("import asyncio\n\nasyncio.run(obj.run)\n")
    entries = EntryPointDetector([mod]).detect()
    assert "myapp.__main__" in entries
    assert "myapp.run" in entries


def test_runner_no_args() -> None:
    mod = _module("import asyncio\n\nasyncio.run()\n")
    assert "myapp.__main__" in EntryPointDetector([mod]).detect()


def test_non_main_block_ignored() -> None:
    mod = _module("if __name__ != '__main__':\n    pass\n\nif flag == '__main__':\n    pass\n")
    assert EntryPointDetector([mod]).detect() == []


def test_bare_decorator_not_framework() -> None:
    mod = _module("@decorator\ndef f():\n    pass\n")
    assert EntryPointDetector([mod]).detect() == []


def test_subscript_decorator_not_framework() -> None:
    mod = _module("@registry['key']\ndef f():\n    pass\n")
    assert EntryPointDetector([mod]).detect() == []


def test_call_result_decorator_not_framework() -> None:
    mod = _module("@factory().route\ndef f():\n    pass\n")
    assert EntryPointDetector([mod]).detect() == []


def test_higher_order_call_not_runner() -> None:
    mod = _module("factory()()\n")
    assert EntryPointDetector([mod]).detect() == []


def test_duplicate_override_dedup() -> None:
    assert resolve_entry_points([], ["a.b", "a.b", ""], []) == ["a.b"]


def test_dunder_main_attribute_call() -> None:
    mod = _module("if __name__ == '__main__':\n    obj.run()\n")
    entries = EntryPointDetector([mod]).detect()
    assert "myapp.__main__" in entries
    assert "myapp.run" in entries


def test_non_compare_if_ignored() -> None:
    mod = _module("if do_work():\n    pass\n")
    assert EntryPointDetector([mod]).detect() == []


def test_higher_order_dunder_call() -> None:
    mod = _module("if __name__ == '__main__':\n    factory()()\n")
    assert "myapp.__main__" in EntryPointDetector([mod]).detect()


def test_runner_attribute_with_call_value() -> None:
    mod = _module("import asyncio\n\nasyncio.run(factory().x)\n")
    assert "myapp.__main__" in EntryPointDetector([mod]).detect()


def test_runner_subscript_target() -> None:
    mod = _module("import asyncio\n\nasyncio.run(arr[0])\n")
    assert "myapp.__main__" in EntryPointDetector([mod]).detect()
