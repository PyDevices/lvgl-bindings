"""The generated MicroPython and CircuitPython modules export ``lv._nesting``.

``_nesting`` is not an LVGL declaration: it is a binding-internal callback
re-entrancy counter, synthesized in ``analyze.py`` and deliberately marked
private in the canonical API model (see ``api_model.build_api_model``).
PyDevices' LVGL coordinator, ``display_driver.py`` (PyDevices/pydevices
``lib/``), gates ``lv.timer_handler()`` on ``lv._nesting.value`` so a pass
never starts from inside an LVGL callback. From inside the generated C the
counter looks unused, since its only reader is that Python code.

Commit cc02710 ("generator: enforce canonical public API semantics") stopped
emitting it as a module global, and c9ff7ee ("generator: remove dead embedded
callback nesting state") then deleted the counter itself. Together they broke
every consumer's LVGL event loop with ``AttributeError: module 'lvgl' has no
attribute '_nesting'``. These tests read the names the freshly generated C
actually exports (``binding.verify_namespace.mp_module_names``), so that drift
fails here instead of on a device.

The other half of the contract, that ``display_driver`` runs a pass with the
counter at rest, stands down while it is raised and stands down quietly when
it is absent (CPython), is tested in pydevices:
``tests/test_lvgl_display_driver.py``.
"""
from __future__ import annotations

from pathlib import Path

from binding.verify_namespace import mp_module_names

REPO_ROOT = Path(__file__).resolve().parents[1]
MICROPYTHON_C = REPO_ROOT / "generated" / "lvgl_micropython.c"
CIRCUITPYTHON_C = REPO_ROOT / "generated" / "lvgl_circuitpython.c"


def test_micropython_globals_expose_nesting_counter():
    names = mp_module_names(MICROPYTHON_C.read_text(encoding="utf-8"))
    assert "_nesting" in names, (
        "generated/lvgl_micropython.c no longer exports _nesting; PyDevices' "
        "display_driver.py reads lv._nesting.value at runtime "
        "(event_loop.task_handler)"
    )


def test_circuitpython_globals_expose_nesting_counter():
    names = mp_module_names(CIRCUITPYTHON_C.read_text(encoding="utf-8"))
    assert "_nesting" in names, (
        "generated/lvgl_circuitpython.c no longer exports _nesting; PyDevices' "
        "display_driver.py reads lv._nesting.value at runtime "
        "(event_loop.task_handler)"
    )
