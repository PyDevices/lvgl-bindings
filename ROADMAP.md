# Roadmap

Work here follows bug reports and requests, so if something is broken or
missing for you, open an [issue](https://github.com/PyDevices/lvgl-bindings/issues).
Two larger changes are planned:

- One repository: lvgl-bindings, lvgl-micropython, lvgl-circuitpython and
  lvgl-python move into a single new repository, `PyDevices/omnipython-lvgl`,
  so the MicroPython, CircuitPython and CPython builds always share one
  bindings commit. The four repositories are archived after the move.

- Vector graphics: enable `LV_USE_VECTOR_GRAPHIC` with ThorVG, so `lv.vector_*`
  and SVG drawing work from Python. ThorVG adds real code size, so for the MCU
  builds this is a build-size question to measure per board, not a quick flip.
