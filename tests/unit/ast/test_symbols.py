import ast

from pyreach.ast.builder import ModuleAST

# We will create this module in the implementation phase
from pyreach.ast.symbols import SymbolTableBuilder


def make_module(
    source: str, module_fqn: str = "test_pkg.test_mod", file_path: str = "dummy.py"
) -> ModuleAST:
    tree = ast.parse(source)
    return ModuleAST(
        file_path=file_path, module_fqn=module_fqn, tree=tree, symbol_table={}, imports={}
    )


def test_import_plain():
    mod = make_module("import os")
    builder = SymbolTableBuilder(mod, lambda x: None)
    symbols = builder.build()
    assert symbols["os"] == "os"
    assert "os" in mod.imports


def test_import_alias():
    mod = make_module("import numpy as np")
    builder = SymbolTableBuilder(mod, lambda x: None)
    symbols = builder.build()
    assert symbols["np"] == "numpy"


def test_import_dotted():
    mod = make_module("import a.b.c")
    builder = SymbolTableBuilder(mod, lambda x: None)
    symbols = builder.build()
    assert symbols["a"] == "a"
    assert symbols["a.b.c"] == "a.b.c"


def test_from_import():
    mod = make_module("from collections import OrderedDict")
    builder = SymbolTableBuilder(mod, lambda x: None)
    symbols = builder.build()
    assert symbols["OrderedDict"] == "collections.OrderedDict"


def test_from_import_alias():
    mod = make_module("from collections import OrderedDict as OD")
    builder = SymbolTableBuilder(mod, lambda x: None)
    symbols = builder.build()
    assert symbols["OD"] == "collections.OrderedDict"


def test_relative_import():
    mod = make_module("from . import sibling", module_fqn="pkg.sub.mod")
    builder = SymbolTableBuilder(mod, lambda x: None)
    symbols = builder.build()
    assert symbols["sibling"] == "pkg.sub.sibling"


def test_relative_parent_import():
    mod = make_module("from ..parent import target", module_fqn="pkg.sub.mod")
    builder = SymbolTableBuilder(mod, lambda x: None)
    symbols = builder.build()
    assert symbols["target"] == "pkg.parent.target"


def test_relative_import_no_module():
    mod = make_module("from . import sibling", module_fqn="")
    builder = SymbolTableBuilder(mod, lambda x: None)
    symbols = builder.build()
    assert symbols["sibling"] == "sibling"


def test_relative_import_in_init():
    mod = make_module(
        "from .sibling import utils",
        module_fqn="relative_pkg",
        file_path="relative_pkg/__init__.py",
    )
    builder = SymbolTableBuilder(mod, lambda x: None)
    symbols = builder.build()
    assert symbols["utils"] == "relative_pkg.sibling.utils"


def test_star_import_with_all():
    mod = make_module("from other import *")

    def mock_loader(fqn: str):
        if fqn == "other":
            return make_module(
                "__all__ = ['A', 'B']\ndef A(): pass\ndef B(): pass\ndef C(): pass", "other"
            )
        return None

    builder = SymbolTableBuilder(mod, mock_loader)
    symbols = builder.build()
    assert symbols["A"] == "other.A"
    assert symbols["B"] == "other.B"
    assert "C" not in symbols


def test_star_import_without_all():
    mod = make_module("from other import *")

    def mock_loader(fqn: str):
        if fqn == "other":
            return make_module("def A(): pass\nclass B: pass\nC = 1\n_D = 2", "other")
        return None

    builder = SymbolTableBuilder(mod, mock_loader)
    symbols = builder.build()
    assert symbols["A"] == "other.A"
    assert symbols["B"] == "other.B"
    assert symbols["C"] == "other.C"
    assert "_D" not in symbols  # Private shouldn't be exported


def test_unresolvable_star_marks_star():
    mod = make_module("from missing import *")
    builder = SymbolTableBuilder(mod, lambda x: None)
    symbols = builder.build()
    assert symbols["*"] == "missing.*"


def test_shadowing_last_wins():
    mod = make_module("import os\nfrom my_os import os")
    builder = SymbolTableBuilder(mod, lambda x: None)
    symbols = builder.build()
    assert symbols["os"] == "my_os.os"


def test_circular_star_import_terminates():
    mod = make_module("from other import *", module_fqn="main")

    def mock_loader(fqn: str):
        if fqn == "other":
            return make_module("from main import *\ndef A(): pass", "other")
        if fqn == "main":
            return make_module("from other import *\ndef B(): pass", "main")
        return None

    builder = SymbolTableBuilder(mod, mock_loader)
    symbols = builder.build()
    assert symbols["A"] == "other.A"
    # Shouldn't get stuck in infinite recursion


def test_simple_assignment_alias():
    mod = make_module("import requests\nClient = requests.Session")
    builder = SymbolTableBuilder(mod, lambda x: None)
    symbols = builder.build()
    assert symbols["requests"] == "requests"
    assert symbols["Client"] == "requests.Session"
