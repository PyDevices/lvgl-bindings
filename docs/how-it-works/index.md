# How the LVGL packages fit together

One generator turns LVGL's headers into bindings for three Pythons. Each
interpreter has its own package that builds those bindings into something you
install or flash.

```text
LVGL headers + lv_conf.h
        |
        v
lvgl-bindings: generator, API model, generated C and lvgl.pyi
        |
        +--> lvgl-python        CPython extension, pydevices-lvgl wheels
        +--> lvgl-micropython   MicroPython user C module
        +--> lvgl-circuitpython CircuitPython user C module
```

## The repositories

- **lvgl-bindings** generates the C bindings (`generated/lvgl_*.c`) and the
  type stub (`lvgl.pyi`) for all three targets, and owns the binding release
  tags.
- **lvgl-python** compiles the CPython binding and publishes the versioned
  `pydevices-lvgl` wheels. It is the one package here that is published.
- **lvgl-micropython** and **lvgl-circuitpython** are build repositories. They
  consume the generated bindings and compile them into MicroPython and
  CircuitPython firmware, and publish no package of their own.

lvgl-bindings is the only place the generated bindings, `lv_conf.h` and the
`python/` helpers are edited. The other three hold synced copies, each pinned to
one exact bindings commit recorded in its `LVGL_BINDINGS_COMMIT` file, and a
sync overwrites any edit made there. Nothing moves to another bindings commit
until that repository's own sync is run against a specific commit or release
tag.

## Why one binding

The packages share the same parsed declarations, the same API model, the same
inheritance order and the same diagnostics policy. MicroPython and
CircuitPython share the `mp_obj_t` lowering because CircuitPython embeds the
same object API, and keep their own registration and VM or garbage collector
glue. CPython gets native `PyObject *` code with its own GIL, lock and module
initialization. The runtimes differ in mechanism and not in what you can call:
an API difference has to be a recorded exception, not a side effect of one
package's build system. [Generator architecture](generator-architecture.md) has
the pipeline.

## The pages for each package

- [lvgl-python](lvgl-python.md): the CPython runtime layer, ownership and callbacks.
- [lvgl-micropython](lvgl-micropython.md): the MicroPython user module and its allocator.
- [lvgl-circuitpython](lvgl-circuitpython.md): the CircuitPython user module and its JPEG decoder.

## Driving the display

The binding does not choose a display, an event loop or a board. For that,
pydevices has a `display_driver` module that wires LVGL to a `board_config`:
display flush, input devices and the event loop. It ships with
[pydevices](https://github.com/PyDevices/pydevices), because it needs that
package's `appdev`, `events`, `keys` and `multimer`, and the bindings don't. You
can also use the bindings with plumbing of your own, as
[the first program](../get-started/first-program.md) does.
