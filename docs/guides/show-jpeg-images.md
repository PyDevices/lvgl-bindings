# Show JPEG images

`lv.image` draws PNG and LVGL's own BIN format on every build. A JPEG needs one
more piece, and what that piece is depends on your interpreter. Without it,
`lv.image` draws nothing for a JPEG and raises no error.

```python
import lvgl as lv
import fs_driver

fs_driver.register("S")
image = lv.image(lv.screen_active())
image.set_src("S:photo.jpg")
```

The path after `S:` goes straight to `open()`; see
[Loading fonts at runtime](../reference/fonts.md#loading-with-fs_driver)
for how `fs_driver` works.

## CPython

Nothing to do. The `pydevices-lvgl` wheel compiles the JPEG decoder in and
registers it when you call `lv.init()`.

## MicroPython-compatible firmware

LVGL's built-in JPEG decoder is off in the bindings (`LV_USE_TJPGD` is 0), so
the decoder comes from the
[jpegio](https://github.com/PyDevices/micropython-pydevices/tree/main/modules/jpegio)
module, which registers its own decoder with LVGL when the two are built into
the same firmware. A firmware with lvgl-micropython alone has no JPEG decoder.
The build prints a note when jpegio is missing, so you hear about it then and
not from a blank image.

Name jpegio when you build with
[micropython-pydevices](https://github.com/PyDevices/micropython-pydevices):

```bash
./build_mp.py --port unix --variant pydevices --modules jpegio,lvgl-micropython
```

On a build that has both, `jpegio.register_lvgl_decoder()` and
`jpegio.lvgl_decoders()` report what happened.

## CircuitPython-compatible firmware

lvgl-circuitpython registers CircuitPython's own `lib/tjpgd` as LVGL's JPEG
decoder, so a firmware that has `CIRCUITPY_JPEGIO` on decodes JPEGs. With
`CIRCUITPY_JPEGIO` off the firmware still builds and has no JPEG decoder; PNG
and BIN images still work.

Decoded images are RGB565 with swapped bytes, the format `jpegio` produces. LVGL
swaps them back when it draws onto an RGB565 display. The decoder claims any
file or buffer that starts with the JPEG marker `FF D8`, whatever its extension,
and always decodes at full size.
