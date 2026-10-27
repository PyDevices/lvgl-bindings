# Build MicroPython firmware with LVGL

lvgl-micropython is a MicroPython user C module: it turns the generated LVGL
binding into a module you build into any MicroPython port. You need `git`, and
whatever MicroPython needs to build for your port. Nothing is generated at
build time.

## Where the bindings come from

The build finds [lvgl-bindings](https://github.com/PyDevices/lvgl-bindings) in
the first of three places that exists:

1. `BINDINGS_DIR`, on `make`'s command line or in the environment. CMake ports
   read it from the environment or `-DBINDINGS_DIR=`.
2. An `lvgl-bindings` checkout beside the lvgl-micropython repository, with its
   `lvgl` submodule.
3. Neither: the build fetches the commit named in `LVGL_BINDINGS_COMMIT` into
   `.deps/lvgl-bindings`, with only what it compiles.

The generated binding is committed, so there is nothing to generate. A
checkout you name or put beside the repository is built as it is: if its
generated binding, `lvgl` or `lv_conf.h` differ from the pinned commit, the
build prints a note saying which commit it is building and carries on. To build
exactly the pinned bindings from a checkout of your own:

```bash
git clone https://github.com/PyDevices/lvgl-micropython
git clone https://github.com/PyDevices/lvgl-bindings
git -C lvgl-bindings checkout "$(cat lvgl-micropython/LVGL_BINDINGS_COMMIT)"
git -C lvgl-bindings submodule update --init lvgl
```

## MicroPython 1.29 or later

Add one line to the manifest your build already uses:

```python
include("/path/to/lvgl-micropython/manifest.py")
```

On unix that manifest is `ports/unix/variants/standard/manifest.py`. On esp32
and rp2 it is usually `ports/<port>/boards/manifest.py`, unless your board
brings its own. Then build as usual. The include brings in the `lvgl` C module
and freezes `fs_driver`. On the unix port against MicroPython 1.30
preview, `lvgl.version_major()` and `lvgl.version_minor()` report 9 and 5.

To leave the MicroPython tree alone, write a manifest of your own and pass it
as `FROZEN_MANIFEST=`. That replaces the port's default, so include the default
too (`include("$(PORT_DIR)/variants/standard/manifest.py")` on unix,
`include("$(PORT_DIR)/boards/manifest.py")` on esp32), or you lose `asyncio`
and the port's other frozen modules.

## Older than 1.29

Manifests there have no `c_module()`, so use `USER_C_MODULES` and freeze the
helpers in `lib/` yourself if you want them. On esp32 and rp2, point it at the
lvgl-micropython repository:

```bash
make BOARD=ESP32_GENERIC_S3 USER_C_MODULES=/abs/path/to/lvgl-micropython
```

On Make ports such as unix, point it at the directory that contains the
repository. That builds every module in the directory:

```bash
cd micropython/ports/unix && make USER_C_MODULES=../../..
```

## With other user C modules

To build several modules together on any port, name them in one manifest: the
lvgl-micropython `manifest.py` carries `c_module(".")`, and a manifest that
`include()`s several such files builds them all.
[micropython-pydevices](https://github.com/PyDevices/micropython-pydevices)'
`build_mp.py` does that for you. Name the modules and it builds them on a port,
with upstream's own boards:

```bash
micropython-pydevices/build_mp.py --port unix --variant pydevices --modules displayif,jpegio,lvgl-micropython
```

Add `jpegio` when you want JPEG images:
[Show JPEG images](show-jpeg-images.md) says why.

## Check the build

The binding's smoke test is part of lvgl-bindings. Run it with the interpreter
you built, from a checkout of lvgl-bindings at the pinned commit:

```bash
./micropython/ports/unix/build-standard/micropython ./lvgl-bindings/tools/test_lvgl_smoke.py
```

`import lvgl_micropython; print(lvgl_micropython.__revision__)` tells you which
lvgl-micropython revision a firmware was built from.

## Driving the screen

With [pydevices](https://github.com/PyDevices/pydevices) installed, its
`display_driver` drives LVGL from `machine.Timer`. At an interactive prompt,
create your widgets and drop to the prompt: the timer keeps animations, LVGL
timers and touch input running while you inspect variables. A standalone script
calls `app.run()` for an explicit loop.

```python
import display_driver  # noqa: F401 - initializes display, input, and machine.Timer
import lvgl as lv

scr = lv.screen_active()
btn = lv.button(scr)
btn.center()
label = lv.label(btn)
label.set_text("Hello MicroPython LVGL!")
```

Without pydevices, give LVGL a buffer and a flush callback as the
[first program](../get-started/first-program.md) does.
