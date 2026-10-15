"""Every CPython callback trampoline owns what it touches during the call.

A trampoline looks the Python callback up in a callback dict, which gives a
borrowed reference. The callback may replace or remove its own registration
while it runs (``timer.set_cb(other)`` from inside the timer callback), which
drops the dict's reference, so the trampoline takes its own for the call.

Each argument converter returns a new reference, and ``PyTuple_Pack`` takes
another, so the trampoline releases the converter's. Without that, every
call leaked one reference to each argument (a widget passed to a
``tree_walk`` callback was never freed).

These checks read the generated C, so the template can't drift from them.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CPYTHON_C = REPO_ROOT / "generated" / "lvgl_python.c"

_TRAMPOLINE = re.compile(
    r"^static [^\n]*?(\w+_callback)\([^\n]*\)\n\{\n(.*?)^\}\n",
    re.MULTILINE | re.DOTALL,
)


def _trampolines():
    text = CPYTHON_C.read_text(encoding="utf-8")
    found = {
        name: body
        for name, body in _TRAMPOLINE.findall(text)
        if "PyObject *py_cb = PyDict_GetItemString(callbacks," in body
    }
    assert found, "no callback trampolines found in generated/lvgl_python.c"
    return found


def test_trampolines_hold_the_callback_for_the_call():
    for name, body in _trampolines().items():
        lookup = body.index("PyObject *py_cb = PyDict_GetItemString")
        call = body.index("PyObject_CallObject(py_cb, py_args)")
        incref = body.find("Py_INCREF(py_cb);")
        assert lookup < incref < call, name
        # Two paths leave after the INCREF: a failed argument conversion,
        # and the call itself. The call's DECREF comes before LVGL's lock
        # is taken back, so a finalizer it runs is still "inside" Python.
        assert body.count("Py_DECREF(py_cb);") == 2, name
        released = body.index("Py_DECREF(py_cb);", call)
        assert call < released < body.index("lvpy_reacquire_lock_after_python();"), name


def test_trampolines_release_their_argument_references():
    for name, body in _trampolines().items():
        args = sorted(set(re.findall(r"PyObject \*(py_arg\d+) = ", body)))
        for arg in args:
            assert "Py_XDECREF(%s);" % arg in body, (name, arg)
