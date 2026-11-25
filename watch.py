"""A script used to watch changes in the Python module and update the view."""

import runpy
import sys
import time
import traceback
from pathlib import Path

import build123d  # noqa: F401 (heavy import to be executed once at startup)
import ocp_viewer  # noqa: F401
from watchfiles import PythonFilter, watch

arg = sys.argv[1] if len(sys.argv) > 1 else "main.py"
module = (
    Path(arg).with_suffix("").as_posix().replace("/", ".")
    if arg.endswith(".py")
    else arg
)
protected = set(sys.modules)


def run() -> None:
    """Run the given script."""
    for name in list(sys.modules):
        if name not in protected:
            del sys.modules[name]
    sys.argv = [module]
    start = time.perf_counter()
    try:
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    except (Exception, SystemExit):  # noqa: BLE001
        traceback.print_exc()
    print(f"-> {time.perf_counter() - start:.2f}s")


run()
for _ in watch(".", watch_filter=PythonFilter(ignore_paths=[Path("watch.py")])):
    run()
