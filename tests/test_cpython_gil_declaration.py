"""The generated CPython module declares that it doesn't need the GIL.

On a free-threaded build (3.13t and later) importing an extension that
doesn't declare this turns the GIL back on for the whole process. The
binding declares it right after ``PyModule_Create``, guarded by
``Py_GIL_DISABLED`` so other builds compile the same source. LVGL isn't
thread-safe: the declaration holds because every LVGL call, and every
LVGL object's release, happens on one thread (documented in lvgl-python).
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CPYTHON_C = REPO_ROOT / "generated" / "lvgl_python.c"


def test_module_init_declares_gil_not_used():
    text = CPYTHON_C.read_text(encoding="utf-8")
    init = text[text.index("PyMODINIT_FUNC PyInit_lvgl(void)"):]
    match = re.search(
        r"PyObject \*m = PyModule_Create\(&lvgl_module_def\);\n"
        r"    if \(m == NULL\) \{\n        return NULL;\n    \}\n"
        r"#ifdef Py_GIL_DISABLED\n"
        r"    if \(PyUnstable_Module_SetGIL\(m, Py_MOD_GIL_NOT_USED\) < 0\) \{",
        init,
    )
    assert match, "PyInit_lvgl no longer declares Py_MOD_GIL_NOT_USED after PyModule_Create"
