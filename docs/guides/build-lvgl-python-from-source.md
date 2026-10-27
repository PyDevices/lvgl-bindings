# Build lvgl-python from source

Use the [wheel](../get-started/install.md) when there is one for your platform.
Build from source to change the CPython runtime layer, or to run on a platform
without a wheel. You need only the lvgl-python clone and its `lvgl` submodule:
no MicroPython, CircuitPython or generator.

## What you need

Python 3.11 or later with `pip` and `setuptools`, and the `lvgl` submodule.

On Linux and macOS, a C compiler (GCC or Clang) and the Python headers. On
Debian and Ubuntu:

```bash
sudo apt install python3-dev build-essential
```

On Windows, python.org CPython and the **Microsoft C++ Build Tools** with the
**Desktop development with C++** workload
([Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)).
MinGW cannot build this extension for python.org's Python. Open a new terminal
after installing the Build Tools so `cl.exe` is on `PATH`.

## Build and install

`pip install` compiles the runtime glue, the generated binding and the LVGL
sources into one extension module. Use an editable install while you work, so
the built module beside the checkout stays in step with your rebuilds.

```bash
git clone --recurse-submodules https://github.com/PyDevices/lvgl-python.git
cd lvgl-python
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pip install -e .
.venv/bin/python -c "import lvgl as lv; lv.init(); lv.deinit(); print('ok')"
```

After a plain clone, fetch the submodule with `git submodule update --init lvgl`.

On Windows, from a shell:

```powershell
git submodule update --init lvgl
py -m pip install -e .
py -c "import lvgl as lv; lv.init(); lv.deinit(); print('ok')"
```

The first build compiles every LVGL source and can take several minutes. After
C source changes, an editable install does not recompile on import: run
`pip install -e .` again, or rebuild in place:

```bash
.venv/bin/python setup.py build_ext --inplace
```

Run the unit tests with:

```bash
.venv/bin/python -m unittest discover -s tests
```

## Windows Python from WSL

Keep the repository on the WSL filesystem and install into Windows Python with
`pip.exe`, with no copy to `C:\`:

```bash
cd /path/to/lvgl-python
pip.exe install -e "$(wslpath -w "$PWD")"
python.exe -c "import lvgl as lv; lv.init(); lv.deinit(); print('ok')"
```

## Android

Prefer a prebuilt wheel tagged `android_21_*` for your ABI (`arm64_v8a` or
`x86_64`). The
[android-template `pydeviceslvgl` recipe](https://github.com/PyDevices/android-template/tree/main/p4a_recipes/pydeviceslvgl)
installs a matching wheel when `--extra-index-url` points at TestPyPI, and
cross-compiles from your checkout otherwise. To use your own tree:

```bash
export P4A_pydeviceslvgl_DIR=/path/to/lvgl-python
```

## Pyodide

Native wheels are not loadable in Pyodide. The release builds a
`pyemscripten_2026_0` wasm32 wheel, which you install with `micropip` as shown
in [Install](../get-started/install.md). To rebuild it locally, run this from
the checkout (it downloads the Pyodide build environment and emsdk on first
use):

```bash
pipx run cibuildwheel --platform pyodide
```

Wheels land in `wheelhouse/`.
