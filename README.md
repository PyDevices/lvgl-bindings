![A blue button reading Hello from LVGL on a light gray background](docs/images/hello.png)

# lvgl-bindings

lvgl-bindings generates the LVGL bindings that give MicroPython-compatible,
CircuitPython-compatible and CPython programs the same `import lvgl as lv`,
and its docs are the home for all of them: lvgl-python, lvgl-micropython and
lvgl-circuitpython.

```bash
python -m pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ pydevices-lvgl
```

On a board, LVGL comes with your firmware build:
[lvgl-micropython](https://github.com/PyDevices/lvgl-micropython) and
[lvgl-circuitpython](https://github.com/PyDevices/lvgl-circuitpython).

```python
import lvgl as lv

lv.init()
disp = lv.display_create(240, 120)
disp.set_color_format(lv.COLOR_FORMAT.RGB565)
buf = bytearray(240 * 120 * 2)
disp.set_buffers(buf, None, len(buf), lv.DISPLAY_RENDER_MODE.FULL)
flushed = []
disp.set_flush_cb(lambda d, area, px: (flushed.append(area.get_width()), d.flush_ready()))

button = lv.button(lv.screen_active())
button.center()
label = lv.label(button)
label.set_text("Hello from LVGL")
button.add_event_cb(lambda e: print("clicked"), lv.EVENT.CLICKED, None)
button.send_event(lv.EVENT.CLICKED, None)

lv.tick_inc(50)
lv.refr_now(disp)
print(label.get_text(), "- drew", flushed[-1], "px wide")
```

```text
clicked
Hello from LVGL - drew 240 px wide
```

The picture at the top is the frame that program drew.

[Docs](https://github.com/PyDevices/lvgl-bindings/blob/main/docs/index.md) · [Examples](https://pydevices.github.io/gallery/pyscript/) · [Roadmap](ROADMAP.md)

OmniPython is made by [PyDevices](https://pydevices.com).
