# lvgl-micropython

lvgl-micropython is the MicroPython build glue for LVGL. It combines the
generated LVGL binding with MicroPython user-module build files and a GC-aware
allocator. It publishes no package of its own and it does not generate
bindings: it consumes [lvgl-bindings](https://github.com/PyDevices/lvgl-bindings),
from a checkout you name with `BINDINGS_DIR`, one beside the repository, or the
commit in `LVGL_BINDINGS_COMMIT`, which the build fetches.

[Build MicroPython firmware with LVGL](../guides/build-micropython-firmware-with-lvgl.md)
shows how to use it.

## The pieces

```text
lvgl-bindings generator and pinned generated artifacts
                         |
                         v
lvgl-micropython build glue + GC-aware allocator
                         |
                         v
MicroPython firmware module: import lvgl
                         |
                         v
pydevices' display_driver -> display, input, timers
```

The build glue is `micropython.mk` for Make ports and `micropython.cmake` for
CMake ports. The allocator, `lv_mem_core_micropython.c`, gives LVGL its memory
from the MicroPython garbage-collected heap. A small `lvgl_micropython` module
carries the `__revision__` of the build.

## The pin

A checkout you supply is built as it is. When its generated binding, LVGL or
`lv_conf.h` differ from `LVGL_BINDINGS_COMMIT`, the build prints a note naming
the commit it is building. Only the copy the build fetches for itself has to
match the pin. The generated binding inputs and the synced `fs_driver.py` are
never hand-edited here: they change in lvgl-bindings, then sync.

## Where JPEG fits

LVGL can always draw PNG and its BIN format. JPEG needs the jpegio module in the
same firmware, which registers its decoder when it sees this user module. A
build without it skips JPEGs at run time rather than failing at build time.
[Show JPEG images](../guides/show-jpeg-images.md) has the details.

## Driving the display

`display_driver` is pydevices', not this firmware's. It wires the display,
input and timers, and wants a `board_config` unless your code has already
created an `appdev.App`. At an interactive MicroPython prompt, hardware timer
callbacks keep LVGL active after the script reaches the prompt.
