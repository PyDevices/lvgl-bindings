# Install

LVGL reaches Python three ways, one per interpreter. Pick the section for the
one you use. All three give you `import lvgl as lv` with the same API.

| You use | Package | You get it by |
|---|---|---|
| CPython on a desktop | lvgl-python | `pip install` |
| MicroPython-compatible firmware | lvgl-micropython | building firmware |
| CircuitPython-compatible firmware | lvgl-circuitpython | building firmware |

## CPython, with lvgl-python

The wheel is `pydevices-lvgl` on TestPyPI. `--extra-index-url` lets pip fetch
setuptools and other dependencies from PyPI.

```bash
python -m pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ pydevices-lvgl
```

Check it:

```bash
python -c "import lvgl as lv; lv.init(); lv.deinit(); print('ok')"
```

```text
ok
```

CI builds a wheel per CPython minor version (3.11 to 3.15, and the
free-threaded 3.15t) for Linux x86_64 and Windows x64. There are Android
wheels for 3.13 and 3.14 (`android_21_arm64_v8a` and `android_21_x86_64`) and a
Pyodide wheel for the browser. pip picks the tag that matches your interpreter;
use the same `pip` and `python` you will run.

Pin a version with `pydevices-lvgl==9.5.52`. For an Android build, ask pip for
the platform:

```bash
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ \
  --only-binary=:all: --platform android_21_arm64_v8a pydevices-lvgl
```

In Pyodide, install with micropip:

```python
import micropip
await micropip.install("pydevices-lvgl", index_urls="https://test.pypi.org/simple/")
```

On Windows Python from WSL, use `pip.exe` and `python.exe` the same way:

```bash
pip.exe install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ pydevices-lvgl
python.exe -c "import lvgl as lv; lv.init(); lv.deinit(); print('ok')"
```

An older `pydevices-lvgl` wheel carried `display_driver.py`, which ships in
`pydevices`. Upgrade both in one command, `pip install -U pydevices pydevices-lvgl`.
Upgraded on its own after a `pydevices` that already has the file, pip's
uninstall of the old `pydevices-lvgl` deletes the `display_driver.py` both
wheels wrote; `pip install --force-reinstall --no-deps pydevices` puts it back.

No wheel for your platform? [Build it from source](../guides/build-lvgl-python-from-source.md).

## MicroPython-compatible firmware, with lvgl-micropython

LVGL is a user C module, so it comes with a firmware build. Clone
lvgl-micropython next to your MicroPython checkout:

```bash
git clone https://github.com/PyDevices/lvgl-micropython
```

On MicroPython 1.29 or later, add one line to the manifest your build already
uses. For the unix port that is `ports/unix/variants/standard/manifest.py`:

```python
include("/path/to/lvgl-micropython/manifest.py")
```

Then build as usual, and `import lvgl` works on the result:

```bash
cd micropython/ports/unix
make
```

[Build MicroPython firmware with LVGL](../guides/build-micropython-firmware-with-lvgl.md)
has the other ports, older MicroPython, and the one-command route through
`build_mp.py`. The build fetches the matching LVGL bindings itself; you need
only `git`.

## CircuitPython-compatible firmware, with lvgl-circuitpython

CircuitPython 11 builds user C modules the way MicroPython does, so you hand
lvgl-circuitpython to CircuitPython's own `make` and nothing in the
CircuitPython tree changes:

```bash
git clone https://github.com/PyDevices/lvgl-circuitpython
make -C circuitpython/ports/unix USER_C_MODULES=/path/to/lvgl-circuitpython
```

For a board, `CIRCUITPY_GIFIO=0` goes on the same line, and LVGL adds about
1 MB of firmware, so check the app partition.
[Build CircuitPython firmware with LVGL](../guides/build-circuitpython-firmware-with-lvgl.md)
has the details.

## What each install gives you

The three packages share one binding, so everything after `import lvgl as lv`
is the same. What differs is how the screen is driven. On a board, or on a
desktop with PyDevices, the `display_driver` helper from
[pydevices](https://github.com/PyDevices/pydevices) wires LVGL to the display
and touch for you. Without it, you give LVGL a buffer and a flush callback, as
[the first program](first-program.md) does.
