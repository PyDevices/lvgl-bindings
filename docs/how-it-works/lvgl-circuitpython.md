# lvgl-circuitpython

lvgl-circuitpython integrates the generated LVGL bindings into a CircuitPython
firmware build. It supplies the user C module glue, a GC-aware LVGL allocator,
synced Python helpers and a CircuitPython-specific JPEG decoder. It is not a pip
package and it does not generate the bindings. The bindings revision it is
tested with is recorded in `LVGL_BINDINGS_COMMIT`, and a checkout at another
commit builds with a note saying so.

[Build CircuitPython firmware with LVGL](../guides/build-circuitpython-firmware-with-lvgl.md)
shows how to use it.

## The pieces

```text
lvgl-bindings at the pinned generated revision
                  |
                  v
lvgl-circuitpython user C module glue
                  |
                  +--> CircuitPython shared-bindings and shared-module for lvgl
                  +--> generated C source and header, and the allocator
                  +--> manifest.py (freezes fs_driver when the build
                  |    passes it via FROZEN_MANIFEST)
                  |
                  v
CircuitPython firmware + pydevices: import display_driver, then import lvgl
```

The generated source, header, LVGL pin and configuration must all match the
recorded bindings commit. Generator-owned code and the synced helper are never
edited here: they change in lvgl-bindings, then sync.

## Why the application pumps LVGL

CircuitPython has no `machine.Timer` for this, so after importing
`display_driver` and `lvgl` the application runs `app.run()` or its own
`asyncio` loop to keep LVGL's tasks and events moving.

## The JPEG decoder

LVGL's JPEG support here is CircuitPython's `jpegio`, not LVGL's bundled TJpgDec.
The bindings' `lv_conf.h` sets `LV_USE_TJPGD 0` on CircuitPython, so LVGL's own
`libs/tjpgd` compiles to nothing. `src/lv_jpegio_decoder_circuitpython.c` then
registers CircuitPython's `lib/tjpgd` (compiled whenever `CIRCUITPY_JPEGIO=1`)
as LVGL's decoder through the public `lv_image_decoder_create` API. That gives
each firmware one TJpgDec. Without `CIRCUITPY_JPEGIO` the firmware still links,
and has no JPEG decoder for LVGL. `lv.tjpgd_init` does not exist on
CircuitPython. [Show JPEG images](../guides/show-jpeg-images.md) has the details
you need to use it.
