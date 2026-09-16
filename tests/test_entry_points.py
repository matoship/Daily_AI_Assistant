import importlib
import inspect
from pathlib import Path
import tomllib

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_file:
    SCRIPTS = tomllib.load(project_file)["project"]["scripts"]


@pytest.mark.parametrize("target", SCRIPTS.values(), ids=SCRIPTS.keys())
def test_console_entry_point_accepts_no_arguments(target):
    # Console-script launchers call the registered function with no arguments.
    module_name, attribute_path = target.split(":", maxsplit=1)
    entry_point = importlib.import_module(module_name)
    for attribute in attribute_path.split("."):
        entry_point = getattr(entry_point, attribute)

    assert callable(entry_point), f"{target} must be callable"
    try:
        inspect.signature(entry_point).bind()
    except TypeError as exc:
        pytest.fail(f"{target} must accept a zero-argument call: {exc}")
