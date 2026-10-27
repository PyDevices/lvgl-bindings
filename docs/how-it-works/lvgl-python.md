# lvgl-python

lvgl-python packages LVGL for CPython as the native `lvgl` extension,
distributed under the `pydevices-lvgl` project name. It exposes the same
Python-shaped API as the MicroPython and CircuitPython targets, and it does not
embed or run a MicroPython interpreter.

Most people install a prebuilt wheel and `import lvgl as lv`: they never clone
the repository, initialize its submodule, or compile LVGL.
[Install](../get-started/install.md) shows how.

## Who owns what

lvgl-python owns the CPython runtime layer, the packaging and the tests. The
generator and the canonical API decisions belong to lvgl-bindings. The
generated binding files and the `fs_driver.py` helper are synced into
lvgl-python at one exact bindings commit: they are inputs to the project, not
hand-edited source.

```text
lvgl-bindings (generator and API policy)
        |
        | explicit sync at a recorded 40-character commit
        v
lvgl-python
  |-- generated/lvgl_python.c and lvgl.pyi   generated binding surface
  |-- src/lvpy_runtime.c                     CPython ownership, callbacks, locking
  |-- lvgl/                                  pinned upstream C submodule
  `-- setup.py                               compiles one CPython extension
        |
        v
import lvgl as lv
  |-- generated wrappers convert Python arguments and results
  |-- runtime wrappers manage objects, structs, the GIL and callback lifetime
  `-- the LVGL C core owns widgets, displays, rendering and event dispatch
```

The public API is generated. The lifecycle, ownership and concurrency behavior
behind it is CPython runtime work, in `src/lvpy_runtime.*`.

## A call from Python into LVGL

1. The wheel provides the binary module `lvgl`. Importing it exposes the
   generated module surface: LVGL-style enum namespaces, functions, object
   constructors and struct methods, rather than a separate Python UI model.
2. Widget constructors and methods enter the generated wrappers. They validate
   and convert Python values, take the runtime's LVGL lock where needed, and
   call the matching LVGL C function.
3. The extension does not choose a display, an event loop or a board. With
   pydevices installed, its `display_driver` wires one up; without it you give
   LVGL a buffer and a flush callback.

## Rules the runtime keeps

- **Pair `lv.init()` and `lv.deinit()`** in standalone programs. Callback
  cleanup during interpreter shutdown is covered by the tests.
- **A callback belongs to its registration, not to the widget's Python
  wrapper.** `mp_lv_callback` stores it in a dict that LVGL's event descriptor
  points at, and the runtime drops that dict's one reference when the event is
  removed or the object deleted. The drop waits until no LVGL call or Python
  callback is in flight, because LVGL sends `LV_EVENT_DELETE` to the runtime's
  hook before the user's. Dropping the wrapper neither stops nor leaks the
  callback.
- **A struct's callbacks share one dict reference, owned by the struct.**
  `lv_anim_t` and `lv_timer_t` callbacks work this way: the generated setters
  pass the struct as `containing_struct`. A Python-owned struct releases the
  reference in its dealloc; a timer and each running copy of an animation
  release theirs through LVGL's `ext_data` free callback (`lvpy_timer_bind`,
  `lvpy_anim_bind`), which needs `LV_USE_EXT_DATA`, set for the CPython build
  only.
- **Unsafe C signatures stay out.** Unbounded pointer-to-pointer and variadic
  APIs are omitted unless a conversion has been reviewed, even if that leaves the
  C surface looking incomplete.
- **Availability can differ by target.** The project shares naming and API
  policy with the other runtimes, but it is a CPython extension, and a feature
  may be explicitly different on another target.

## Threads

LVGL is not thread-safe and the binding keeps shared state of its own, so one
thread drives it. [Use LVGL from threads](../guides/use-lvgl-from-threads.md)
explains the rule and what it means on a free-threaded build.
