# Reference

There is no separate API manual for these packages. The binding exposes
LVGL's own C API, so [LVGL's documentation](https://docs.lvgl.io/master/) is
the reference for what each widget, style and function does. This page says
how the C names map to Python, and what the binding leaves out.

The exact names your build has are in the type stub, `lvgl.pyi`. Wheels install
it beside the `lvgl` extension module, and [`generated/lvgl.pyi`](../../generated/lvgl.pyi) in
[lvgl-bindings](https://github.com/PyDevices/lvgl-bindings/blob/main/generated/lvgl.pyi)
is the shared copy. If your checker doesn't pick it up, set
`python.analysis.stubPath` (Pylance) or `stubPath` (pyright) to a directory
that holds `lvgl.pyi`.

## How C names become Python names

The binding follows LVGL's own naming, minus the `lv_` prefix.

| Pattern | Example |
|---------|---------|
| Symbol namespace | `lv.SYMBOL.OK`, `lv.SYMBOL.CANCEL` |
| Enum namespaces | `lv.COLOR_FORMAT.RGB565`, `lv.DISPLAY_RENDER_MODE.PARTIAL` |
| Widget types (callable) | `lv.obj()`, `lv.label(parent)`, `lv.button(parent)` |
| Object methods | `label.set_text("...")`, `scr.add_event_cb(cb, lv.EVENT.CLICKED, None)` |
| Module functions | `lv.display_create(240, 240)`, `lv.screen_active()` |
| Struct methods | `event.get_code()` on `lv_event_t` wrappers |

Struct-backed APIs, including displays, use methods the same way on all three
interpreters: `disp.set_flush_cb(...)`, `disp.set_render_mode(...)`.

There is one public spelling of each name across MicroPython-compatible,
CircuitPython-compatible and CPython builds.

## What the binding leaves out

- **Unsafe C signatures are absent.** Variadic functions and unbounded
  pointer-to-pointer APIs are omitted unless the generator has a reviewed safe
  conversion.
- **A callback lives as long as its registration.** `add_event_cb(handler, ...)`
  holds your handler (and a `user_data` dict, if you pass one) until the widget
  is deleted or the event is removed; then the binding lets them go. Dropping
  your Python reference to the widget does not stop the callback while the widget
  exists, and a handler may delete its own widget. Callbacks set on an
  `lv.anim_t` live while the Python struct or a running copy of it exists; a
  timer's callback lives while the timer does.
- **One thread drives LVGL.** See [Use LVGL from threads](../guides/use-lvgl-from-threads.md).
- **JPEG needs a decoder** on firmware: see [Show JPEG images](../guides/show-jpeg-images.md).

## Fonts

[Fonts](fonts.md) covers the font files you can load at runtime without a
firmware rebuild, the `fs_driver` helper that loads them, and converting your
own.
