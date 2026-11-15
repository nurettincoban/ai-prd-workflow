"""Test helpers: load the extensionless `td` program and isolate the environment."""
import contextlib
import importlib.machinery
import importlib.util
import os
import pathlib
import tempfile

TD_PATH = pathlib.Path(__file__).resolve().parent.parent / "td"


def load_td():
    """Load the td program as a module named td and return it."""
    loader = importlib.machinery.SourceFileLoader("td", str(TD_PATH))
    spec = importlib.util.spec_from_loader("td", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@contextlib.contextmanager
def temp_env():
    """Yield a temp directory with HOME and TD_FILE (<tmp>/tasks.json) set; restore both on exit."""
    saved = {k: os.environ.get(k) for k in ("HOME", "TD_FILE")}
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HOME"] = tmp
        os.environ["TD_FILE"] = os.path.join(tmp, "tasks.json")
        try:
            yield tmp
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
