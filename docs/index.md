# LVGL for Python

[LVGL](https://lvgl.io/) is a C graphics library for small displays. These
packages let you drive it from Python, on a desktop with CPython and on a
board with MicroPython-compatible or CircuitPython-compatible firmware. All
three share one API, generated from LVGL's headers, so a program you write
against `import lvgl as lv` runs on each.

```python
import lvgl as lv

lv.init()
disp = lv.display_create(240, 120)
# ... a button and a label, as in the first program
```

[Install it](get-started/install.md) for the Python you use, then run
[your first program](get-started/first-program.md). The
[guides](guides/use-lvgl-from-threads.md) take one task each, the
[reference](reference/index.md) lists the names and the fonts, and
[How it works](how-it-works/index.md) explains how the three packages relate.

```{toctree}
:hidden:
:caption: Get started

get-started/install
get-started/first-program
```

```{toctree}
:hidden:
:caption: Guides

guides/use-lvgl-from-threads
guides/show-jpeg-images
guides/build-lvgl-python-from-source
guides/build-micropython-firmware-with-lvgl
guides/build-circuitpython-firmware-with-lvgl
guides/flash-lvgl-circuitpython-on-a-qualia
```

```{toctree}
:hidden:
:caption: Reference

reference/index
reference/fonts
```

```{toctree}
:hidden:
:caption: How it works

how-it-works/index
how-it-works/generator-architecture
how-it-works/lvgl-python
how-it-works/lvgl-micropython
how-it-works/lvgl-circuitpython
```

```{toctree}
:hidden:
:caption: Changelog

changelog
```
