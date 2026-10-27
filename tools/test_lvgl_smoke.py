#!/usr/bin/env python3
"""Unified LVGL binding smoke tests for MicroPython, CircuitPython, and CPython.

Run with the target interpreter after building that port, for example:

  # MicroPython unix
  ./micropython/ports/unix/build-standard/micropython \\
    ./lvgl-bindings/tools/test_lvgl_smoke.py

  # CircuitPython unix
  ./circuitpython/ports/unix/build-coverage/micropython \\
    ./lvgl-bindings/tools/test_lvgl_smoke.py

  # CPython (WSL venv)
  ./lvgl-python/.venv/bin/python ./lvgl-bindings/tools/test_lvgl_smoke.py

Exercises init/deinit, headless display, widgets, event callbacks, GC visibility,
and CPython-specific struct/Blob helpers where applicable.
"""
import gc
import sys


def _fail(msg):
    print("FAIL: {}".format(msg), file=sys.stderr)
    raise SystemExit(1)


def _warn(msg):
    print("WARN: {}".format(msg), file=sys.stderr)


def _lv_export(lv, name):
    """Resolve an established module-level export."""
    return getattr(lv, name, None)


def _widget_type(lv, name):
    return _lv_export(lv, name)


def _widget_attr(obj, name):
    return getattr(obj, name)


def _module_defines(module, name):
    namespace = getattr(module, "__dict__", None)
    if namespace is not None:
        return name in namespace
    return name in dir(module)


def _is_cpython():
    impl = getattr(sys, "implementation", None)
    return impl is not None and impl.name == "cpython"


def _runtime_target():
    impl = getattr(sys, "implementation", None)
    name = getattr(impl, "name", "")
    if name == "cpython":
        return "cpython"
    if name == "circuitpython":
        return "circuitpython"
    return "micropython"


def _prepare_import_path():
    """Avoid lvgl-bindings/lvgl submodule shadowing the compiled CPython extension."""
    if not _is_cpython():
        return
    import os.path as ospath

    here = ospath.dirname(ospath.abspath(__file__))
    lvgl_sub = ospath.join(here, "lvgl")
    if ospath.isdir(lvgl_sub):
        norm = ospath.normpath
        sys.path[:] = [p for p in sys.path if norm(p) != norm(here)]
    cpy_mod = ospath.join(ospath.dirname(here), "lvgl-python")
    if ospath.isdir(cpy_mod) and cpy_mod not in sys.path:
        sys.path.insert(0, cpy_mod)


def _import_lv():
    _prepare_import_path()
    import lvgl as lv  # noqa: WPS433 — runtime import under test

    return lv


def _is_initialized(lv):
    if hasattr(lv, "is_initialized"):
        return lv.is_initialized()
    return False


def _setup_display(lv, width=240, height=240):
    """Minimal headless display so screen_active() and widgets behave like embedded."""

    def flush_cb(disp, area, color_p):
        disp.flush_ready()

    disp = lv.display_create(width, height)
    disp.set_flush_cb(flush_cb)

    if hasattr(disp, "set_color_format"):
        disp.set_color_format(_lv_export(lv, "COLOR_FORMAT").RGB565)
    elif hasattr(lv, "display_set_color_format"):
        lv.display_set_color_format(disp, _lv_export(lv, "COLOR_FORMAT").RGB565)

    buf = lv.draw_buf_create(width, height, _lv_export(lv, "COLOR_FORMAT").RGB565, 0)

    if hasattr(disp, "set_draw_buffers"):
        disp.set_draw_buffers(buf, None)
    elif hasattr(lv, "display_set_draw_buffers"):
        lv.display_set_draw_buffers(disp, buf, None)

    if hasattr(disp, "set_render_mode"):
        disp.set_render_mode(_lv_export(lv, "DISPLAY_RENDER_MODE").PARTIAL)
    elif hasattr(lv, "display_set_render_mode"):
        lv.display_set_render_mode(disp, _lv_export(lv, "DISPLAY_RENDER_MODE").PARTIAL)

    return disp, buf


def _teardown_display(buf):
    if buf is not None and hasattr(buf, "destroy"):
        buf.destroy()


def test_import_and_constants(lv):
    if not _is_cpython():
        return
    if not hasattr(lv, "init") or not hasattr(lv, "deinit"):
        _fail("lvgl module missing init/deinit")
    print("OK: import lvgl; init/deinit")


def test_basic(lv):
    lv.init()
    if hasattr(lv, "is_initialized") and not lv.is_initialized():
        _fail("lv.init() did not initialize LVGL")
    assert hasattr(lv, "deinit")
    assert _widget_type(lv, "label") is not None or _widget_type(lv, "obj") is not None
    event = _lv_export(lv, "EVENT")
    assert event is not None and hasattr(event, "CLICKED")
    print("OK: import lvgl; lv.init(); core symbols present")


def test_string_constants(lv):
    symbol = _lv_export(lv, "SYMBOL")
    if symbol is None:
        return
    for name in ("OK", "CLOSE", "HOME"):
        if not hasattr(symbol, name):
            _fail("missing lv.SYMBOL.{}".format(name))
    print("OK: LVGL SYMBOL namespace (lv.SYMBOL.OK, …)")


def test_enums(lv):
    event = _lv_export(lv, "EVENT")
    clicked = event.CLICKED
    if not isinstance(clicked, int) or clicked <= 0:
        _fail("lv.EVENT.CLICKED unexpected value: {!r}".format(clicked))
    obj_type = _widget_type(lv, "obj")
    flag = _widget_attr(obj_type, "FLAG")
    if flag is None or not hasattr(flag, "SCROLLABLE"):
        _fail("lv.obj missing FLAG enum namespace")
    if flag.SCROLLABLE != (1 << 4):
        _fail("lv.obj.FLAG.SCROLLABLE unexpected value")
    module_flag = _lv_export(lv, "OBJ_FLAG")
    if module_flag is None or not hasattr(module_flag, "SCROLLABLE"):
        _fail("lv.OBJ_FLAG missing at module level")
    if module_flag.SCROLLABLE != flag.SCROLLABLE:
        _fail("lv.OBJ_FLAG.SCROLLABLE must match lv.obj.FLAG.SCROLLABLE")
    label_type = _widget_type(lv, "label")
    if _widget_attr(label_type, "LONG_MODE") is None:
        _fail("lv.label missing LONG_MODE enum namespace")
    if _lv_export(lv, "LABEL_LONG_MODE") is not None:
        _fail("lv.LABEL_LONG_MODE must not be exposed at module level")
    print("OK: enum namespaces (lv.EVENT, lv.OBJ_FLAG, lv.obj.FLAG, lv.label.LONG_MODE)")


def test_enum_dir(lv):
    # dir() must list enum members, or tab completion and help() find nothing
    # (lvgl-bindings#18: CPython resolved members only through tp_getattro).
    image_align = _widget_attr(_widget_type(lv, "image"), "ALIGN")
    cases = (
        ("lv.EVENT", _lv_export(lv, "EVENT"), "CLICKED"),
        ("lv.ALIGN", _lv_export(lv, "ALIGN"), "CENTER"),
        ("lv.image.ALIGN", image_align, "CONTAIN"),
        ("lv.obj.FLAG", _widget_attr(_widget_type(lv, "obj"), "FLAG"), "SCROLLABLE"),
        ("lv.SYMBOL", _lv_export(lv, "SYMBOL"), "OK"),
    )
    for label, ns, expected in cases:
        names = [n for n in dir(ns) if not n.startswith("_")]
        if expected not in names:
            _fail("dir({}) lacks {} (got {} names)".format(label, expected, len(names)))
        for name in names:
            try:
                getattr(ns, name)
            except AttributeError:
                _fail("dir({}) lists {} but getattr fails".format(label, name))
    print("OK: dir() lists enum members (lv.EVENT, lv.image.ALIGN, lv.SYMBOL, ...)")


def test_module_types(lv):
    for name in ("C_Pointer", "LvReferenceError"):
        if not hasattr(lv, name):
            _fail("missing module export lv.{}".format(name))
    for name in ("Blob", "Struct", "mp_lv_init_gc", "mp_lv_deinit_gc", "mp_lv_get_roots"):
        if hasattr(lv, name):
            _fail("private implementation export leaked as lv.{}".format(name))
    # _nesting is a deliberate, audited exception to the private-export
    # policy above: it is the binding-internal callback re-entrancy
    # counter that PyDevices' display_driver.py (pydevices lib/) reads at
    # runtime as lv._nesting.value to guard
    # against reentrant lv.task_handler() calls. It is private in the
    # canonical API model (visibility="private" in api_model.py) but is
    # still deliberately emitted for MicroPython/CircuitPython -- see
    # emit_backend.module_registration_plan, the blob-table loop in
    # emit_c_micropython_style.py, and docs/how-it-works/generator-architecture.md's
    # "Public API policy" section. CPython never emitted it (its own
    # ContextVar-scoped lvpy_nesting_inc/dec serves the same purpose) so it
    # stays forbidden there.
    if _is_cpython():
        if hasattr(lv, "_nesting"):
            _fail("private implementation export leaked as lv._nesting")
    else:
        if not hasattr(lv, "_nesting"):
            _fail(
                "lv._nesting missing; PyDevices' display_driver.py "
                "task_handler()/async_refresh() read lv._nesting.value "
                "and will raise AttributeError at runtime"
            )
    if hasattr(lv, "area_get_width"):
        _fail("struct method leaked as module-level lv.area_get_width")
    if _module_defines(lv, "__init__") or _module_defines(lv, "__del__"):
        _fail("generated lifecycle dunder leaked from module")
    print("OK: common module helpers and private-export policy")


def test_struct_helpers(lv):
    color_t = _lv_export(lv, "color_t")
    size = color_t.__SIZE__
    if not isinstance(size, int) or size <= 0:
        _fail("lv.color_t.__SIZE__ missing or invalid")
    for name in ("__cast__", "__dereference__", "__cast_instance__"):
        if not hasattr(color_t, name):
            _fail("lv.color_t missing helper {}".format(name))
    print("OK: struct helpers (__SIZE__, __cast__, …)")


def test_widget_types(lv):
    for name in ("obj", "label", "button"):
        if _widget_type(lv, name) is None:
            _fail("missing widget type lv.{}".format(name))
    print("OK: widget types registered (lv.obj, lv.label, …)")


def test_module_functions(lv):
    for name in ("display_create", "screen_active", "tick_inc"):
        if not hasattr(lv, name):
            _fail("missing module function lv.{}".format(name))
    if _is_cpython() and not hasattr(lv, "refr_now"):
        _fail("missing module function lv.refr_now")
    print("OK: module functions (display_create, screen_active, …)")


def test_refr_now(lv, disp=None):
    if not _is_cpython() or not hasattr(lv, "refr_now"):
        return
    own_disp = False
    own_buf = None
    if disp is None:
        disp = lv.display_create(80, 80)
        own_buf = lv.draw_buf_create(80, 8, _lv_export(lv, "COLOR_FORMAT").RGB565, 0)
        if hasattr(lv, "display_set_draw_buffers"):
            lv.display_set_draw_buffers(disp, own_buf, None)
        else:
            disp.set_draw_buffers(own_buf, None)
        if hasattr(lv, "display_set_render_mode"):
            lv.display_set_render_mode(disp, _lv_export(lv, "DISPLAY_RENDER_MODE").PARTIAL)
        else:
            disp.set_render_mode(_lv_export(lv, "DISPLAY_RENDER_MODE").PARTIAL)
        disp.set_flush_cb(lambda d, area, color_p: d.flush_ready())
        own_disp = True
    before = lv.display_get_default()
    lv.refr_now(disp)
    after = lv.display_get_default()
    if before is None or after is None:
        _fail("display_get_default() returned None around refr_now")
    if lv.screen_active() is None:
        _fail("screen_active() returned None after refr_now")
    if own_disp:
        _teardown_display(own_buf)
        if hasattr(disp, "delete"):
            disp.delete()
        elif hasattr(lv, "display_delete"):
            lv.display_delete(disp)
    print("OK: refr_now refreshes without deleting the display")


def test_widget(lv):
    scr = lv.screen_active()
    label = _widget_type(lv, "label")(scr)
    label.set_text("lvgl smoke")
    if label.get_text() != "lvgl smoke":
        _fail("label text mismatch: {!r}".format(label.get_text()))
    print("OK: label create/set_text on active screen")


def test_event_callback(lv):
    scr = lv.screen_active()
    fired = []

    def on_clicked(event):
        fired.append(event.get_code())

    scr.add_event_cb(on_clicked, _lv_export(lv, "EVENT").CLICKED, None)
    scr.send_event(_lv_export(lv, "EVENT").CLICKED, None)
    if not fired:
        _fail("screen CLICKED callback did not run")
    print("OK: add_event_cb + send_event")


def test_callback_gc_with_widget_ref(lv):
    scr = lv.screen_active()
    fired = []

    def handler(event):
        fired.append(1)

    scr.add_event_cb(handler, _lv_export(lv, "EVENT").CLICKED, None)
    del handler
    gc.collect()
    scr.send_event(_lv_export(lv, "EVENT").CLICKED, None)
    if not fired:
        _fail("callback was collected while its widget remained referenced")
    print("OK: callback survived gc.collect() while widget referenced")


def test_button_callback(lv):
    scr = lv.screen_active()
    fired = []

    def on_click(event):
        if event.get_code() == _lv_export(lv, "EVENT").CLICKED:
            fired.append(1)

    btn = _widget_type(lv, "button")(scr)
    btn.set_size(80, 40)
    btn.add_event_cb(on_click, _lv_export(lv, "EVENT").CLICKED, None)
    btn.send_event(_lv_export(lv, "EVENT").CLICKED, None)
    if not fired:
        _fail("button CLICKED callback did not run")
    print("OK: button event callback")


def test_callback_gc_without_widget_ref(lv):
    scr = lv.screen_active()
    fired = []

    def on_click(event):
        if event.get_code() == _lv_export(lv, "EVENT").CLICKED:
            fired.append(1)

    btn = _widget_type(lv, "button")(scr)
    btn.add_event_cb(on_click, _lv_export(lv, "EVENT").CLICKED, None)
    del on_click
    btn_idx = scr.get_child_count() - 1
    del btn
    gc.collect()

    child = scr.get_child(btn_idx)
    child.send_event(_lv_export(lv, "EVENT").CLICKED, None)
    if not fired:
        _fail("callback was collected while its LVGL widget remained reachable")
    print("OK: callback survived gc with widget reached through get_child")


def test_multi_callbacks(lv):
    scr = lv.screen_active()
    btn = _widget_type(lv, "button")(scr)
    btn.set_size(80, 40)
    fired = []

    def mk(name):
        def cb(event):
            fired.append((name, event.get_code()))

        return cb

    event = _lv_export(lv, "EVENT")
    for name, code in (
        ("PRESSED", event.PRESSED),
        ("RELEASED", event.RELEASED),
        ("CLICKED", event.CLICKED),
    ):
        btn.add_event_cb(mk(name), code, None)

    btn.send_event(event.PRESSED, None)
    btn.send_event(event.CLICKED, None)
    btn.send_event(event.RELEASED, None)

    expected = [
        ("PRESSED", event.PRESSED),
        ("CLICKED", event.CLICKED),
        ("RELEASED", event.RELEASED),
    ]
    if fired != expected:
        _fail("multi-callback dispatch mismatch: got {!r}, expected {!r}".format(fired, expected))
    print("OK: multiple filtered callbacks on one object")


def test_pointer_buffer_dereference(lv, main_disp=None):
    disp = lv.display_create(16, 16)
    own_buf = lv.draw_buf_create(16, 4, _lv_export(lv, "COLOR_FORMAT").RGB565, 0)
    if hasattr(lv, "display_set_draw_buffers"):
        lv.display_set_draw_buffers(disp, own_buf, None)
    else:
        disp.set_draw_buffers(own_buf, None)
    seen = []

    def flush_cb(d, area, color_p):
        width = area.x2 - area.x1 + 1
        height = area.y2 - area.y1 + 1
        data = color_p.__dereference__(width * height * 2)
        raw_pointer = color_p.__cast__()
        typed_pointer = color_p.__cast__(_lv_export(lv, "color_t"))
        if not isinstance(raw_pointer, int):
            _fail("Blob.__cast__() did not return a pointer-sized integer")
        if not isinstance(typed_pointer, _lv_export(lv, "color_t")):
            _fail("Blob.__cast__(type) did not return the requested type")
        seen.append(len(data))
        d.flush_ready()

    disp.set_flush_cb(flush_cb)
    lv.refr_now(disp)
    if not seen:
        _fail("flush callback did not run during refr_now")
    if main_disp is not None:
        if hasattr(lv, "display_set_default"):
            lv.display_set_default(main_disp)
        elif hasattr(main_disp, "set_default"):
            main_disp.set_default()
    _teardown_display(own_buf)
    if hasattr(disp, "delete"):
        disp.delete()
    elif hasattr(lv, "display_delete"):
        lv.display_delete(disp)
    print("OK: opaque pointer dereference and typed cast in flush callback")


def test_remove_style_none(lv):
    part = _lv_export(lv, "PART")
    if part is None:
        return
    scr = lv.screen_active()
    arc = _widget_type(lv, "arc")(scr)
    arc.set_size(40, 40)
    arc.remove_style(None, part.KNOB)
    print("OK: arc.remove_style(None, PART.KNOB)")


def test_struct_fields_and_arrays(lv):
    area = _lv_export(lv, "area_t")()
    area.x1 = 3
    area.y1 = 5
    area.x2 = 13
    area.y2 = 17
    if (area.x1, area.y1, area.x2, area.y2) != (3, 5, 13, 17):
        _fail("struct field read/write mismatch")
    if area.get_width() != 11 or area.get_height() != 13:
        _fail("struct method did not observe updated fields")

    scr = lv.screen_active()
    line = _widget_type(lv, "line")(scr)
    point_type = _lv_export(lv, "point_precise_t")
    points = point_type(2)
    first = point_type()
    second = point_type()
    first.x, first.y = 1, 2
    second.x, second.y = 8, 9
    points[0] = first
    points[1] = second
    line.set_points(points, 2)
    print("OK: struct fields, struct methods, and typed array conversion")


def _line_size(lv, line):
    line.invalidate()
    lv.screen_active().update_layout()
    return line.get_width(), line.get_height()


def test_line_points_list_and_buffer(lv):
    # The same set_points call takes a list of points (structs or dicts) and a
    # packed buffer on every interpreter (lvgl-bindings#37).
    import struct

    point_type = _lv_export(lv, "point_precise_t")
    probe = point_type()
    probe.x = 1.5
    fmt = "<ff" if probe.x == 1.5 else "<ii"
    xy = [(0, 0), (40, 20), (80, 0)]
    as_dicts = [{"x": x, "y": y} for x, y in xy]
    as_structs = []
    for x, y in xy:
        p = point_type()
        p.x, p.y = x, y
        as_structs.append(p)
    as_buf = bytearray()
    for x, y in xy:
        as_buf += struct.pack(fmt, x, y)

    scr = lv.screen_active()
    sizes = {}
    for name, pts in (
        ("list of dicts", as_dicts),
        ("list of structs", as_structs),
        ("tuple of dicts", tuple(as_dicts)),
        ("packed buffer", as_buf),
    ):
        line = _widget_type(lv, "line")(scr)
        try:
            line.set_points(pts, len(xy))
        except Exception as exc:
            _fail("line.set_points rejected a %s: %s: %s" % (name, type(exc).__name__, exc))
        # The converted array must outlive the list it came from: LVGL keeps
        # the pointer.
        pts = None
        gc.collect()
        sizes[name] = _line_size(lv, line)
        line.delete()
    if len(set(sizes.values())) != 1 or sizes["list of dicts"][0] < 80:
        _fail("line.set_points forms disagree: %r" % (sizes,))
    line = _widget_type(lv, "line")(scr)
    try:
        line.set_points([{"x": 1}, 5], 2)
    except (TypeError, SyntaxError):
        pass
    else:
        _fail("line.set_points accepted a list holding an int")
    line.delete()
    print("OK: line.set_points takes a list of points or a packed buffer")


def test_struct_array_fields(lv):
    # A fixed-size struct array inside a struct (lv_point_precise_t p[3]) reads
    # as a view: index reads and writes go through to the struct, len() works,
    # and a wrong-sized or wrong-typed assignment raises and changes nothing
    # (lvgl-bindings#38).
    point_type = _lv_export(lv, "point_precise_t")
    d = _lv_export(lv, "draw_triangle_dsc_t")()
    d.init()
    if len(d.p) != 3:
        _fail("len(draw_triangle_dsc_t.p) is %r, not 3" % (len(d.p),))
    d.p[0].x = 5
    d.p[1] = point_type({"x": 7, "y": 8})
    d.p[2] = {"x": 9, "y": 10}
    got = [(p.x, p.y) for p in d.p]
    if got != [(5, 0), (7, 8), (9, 10)]:
        _fail("struct array item writes were lost: %r" % (got,))
    d.p = [{"x": 20, "y": 200}, point_type({"x": 180, "y": 20}), {"x": 340, "y": 200}]
    want = [(20, 200), (180, 20), (340, 200)]
    if [(p.x, p.y) for p in d.p] != want:
        _fail("whole struct array assignment was lost")
    for bad in ([{"x": 1, "y": 1}], [{"x": 1}, {"x": 2}, 5], 5, None):
        try:
            d.p = bad
        except (TypeError, ValueError, SyntaxError):
            pass
        else:
            _fail("struct array accepted %r" % (bad,))
        if [(p.x, p.y) for p in d.p] != want:
            _fail("a rejected struct array assignment changed the field: %r" % (bad,))
    try:
        d.p[3]
    except IndexError:
        pass
    else:
        _fail("struct array index 3 of 3 did not raise IndexError")
    # The view keeps the struct it came from alive.
    view = d.p
    d = None
    gc.collect()
    if (view[2].x, view[2].y) != (340, 200):
        _fail("struct array view lost its struct")

    g = _lv_export(lv, "grad_dsc_t")()
    g.stops[1].frac = 200
    g.stops[0] = {"frac": 10, "opa": 255}
    if (len(g.stops), g.stops[0].frac, g.stops[1].frac) != (2, 10, 200):
        _fail("grad_dsc_t.stops writes were lost")
    print("OK: struct array fields index, assign and check their length")


def test_grad_helpers(lv):
    # The gradient helpers are methods named as the stub names them, and the
    # params union they fill in is readable and writable (lvgl-bindings#39).
    g = _lv_export(lv, "grad_dsc_t")()
    for name in ("linear_init", "radial_init", "radial_set_focal", "conical_init",
                 "horizontal_init", "vertical_init", "init_stops"):
        if not hasattr(g, name):
            _fail("grad_dsc_t has no %s" % name)
    pad = lv.GRAD_EXTEND.PAD
    g.linear_init(1, 2, 3, 4, pad)
    lin = g.params.linear
    if (lin.start.x, lin.start.y, lin.end.x, lin.end.y) != (1, 2, 3, 4):
        _fail("linear_init did not fill params.linear")
    if g.dir != lv.GRAD_DIR.LINEAR:
        _fail("linear_init did not set dir")
    g.radial_init(80, 80, 160, 80, pad)
    rad = g.params.radial
    if (rad.end.x, rad.end.y, rad.end_extent.x, rad.end_extent.y) != (80, 80, 160, 80):
        _fail("radial_init did not fill params.radial")
    g.conical_init(50, 60, 0, 1800, pad)
    con = g.params.conical
    if (con.center.x, con.start_angle, con.end_angle) != (50, 0, 1800):
        _fail("conical_init did not fill params.conical")
    con.end_angle = 900
    if g.params.conical.end_angle != 900:
        _fail("a write through params.conical was lost")
    print("OK: gradient helpers by stub name; params reads and writes")


def test_struct_dir(lv):
    # dir() on a struct instance lists its fields and methods, so they can be
    # discovered from the REPL (lvgl-bindings#40).
    want = {
        "grad_dsc_t": ("stops", "dir", "extend", "params", "linear_init"),
        "draw_triangle_dsc_t": ("p", "color", "opa", "init"),
        "area_t": ("x1", "y1", "x2", "y2", "get_width"),
    }
    for name, attrs in want.items():
        listed = dir(_lv_export(lv, name)())
        missing = [a for a in attrs if a not in listed]
        if missing:
            _fail("dir(%s()) is missing %r" % (name, missing))
    print("OK: dir() on a struct lists its fields and methods")


def test_struct_methods_by_value(lv):
    # Struct methods that take their struct by value, not by pointer, are
    # methods on every runtime (lvgl-bindings#46).
    c = lv.color_hex(0x336699)
    if (c.red, c.green, c.blue) != (0x33, 0x66, 0x99):
        _fail("color_hex gave %r" % ((c.red, c.green, c.blue),))
    if c.to_u32() & 0xFFFFFF != 0x336699:
        _fail("color_t.to_u32() is %r" % (c.to_u32(),))
    if not c.eq(lv.color_hex(0x336699)) or c.eq(lv.color_hex(0x000000)):
        _fail("color_t.eq() is wrong")
    if not 0 < c.brightness() < 255:
        _fail("color_t.brightness() is %r" % (c.brightness(),))
    lighter = c.lighten(128)
    if lighter.red <= c.red:
        _fail("color_t.lighten() did not lighten: %r" % (lighter.red,))
    if (c.red, c.green, c.blue) != (0x33, 0x66, 0x99):
        _fail("a by-value method changed its receiver")
    c32 = c.to_32(255)
    if (c32.red, c32.alpha) != (0x33, 255) or not c32.eq(c.to_32(255)):
        _fail("color_t.to_32() or color32_t.eq() is wrong")
    for type_name, names in (
        ("color16_t", ("luminance", "to_color")),
        ("color32_t", ("color_mix32", "color_over32", "luminance")),
        ("area_t", ("diff",)),
        ("layout_callbacks_t", ("create",)),
    ):
        obj = _lv_export(lv, type_name)()
        missing = [n for n in names if not hasattr(obj, n)]
        if missing:
            _fail("%s has no %r" % (type_name, missing))
    print("OK: struct methods that take the struct by value")


def test_struct_value_from_dict(lv):
    # A struct-by-value field takes a dict, as its type's constructor does, and
    # a wrong type raises instead of crashing CPython (lvgl-bindings#21).
    dsc_type = _lv_export(lv, "image_dsc_t")
    dsc = dsc_type({"header": {"w": 4, "h": 3}, "data_size": 12})
    if (dsc.header.w, dsc.header.h, dsc.data_size) != (4, 3, 12):
        _fail("nested dict did not build the struct field")
    dsc.header = {"w": 7}
    if (dsc.header.w, dsc.header.h) != (7, 0):
        _fail("dict assignment to a struct field did not replace it")
    for bad in (5, "x"):
        try:
            dsc.header = bad
        except TypeError:
            pass
        except Exception:
            if _is_cpython():
                _fail("wrong type for a struct field raised something other than TypeError")
        else:
            _fail("wrong type for a struct field was accepted: %r" % (bad,))
    if dsc.header.w != 7:
        _fail("a rejected assignment changed the struct field")
    print("OK: struct fields by value from dicts; wrong types raise")


def test_callback_deletion(lv):
    btn = _widget_type(lv, "button")(lv.screen_active())
    fired = []

    def callback(event):
        fired.append(1)

    descriptor = btn.add_event_cb(callback, _lv_export(lv, "EVENT").CLICKED, None)
    if not btn.remove_event_dsc(descriptor):
        _fail("remove_event_dsc did not report a removed callback")
    btn.send_event(_lv_export(lv, "EVENT").CLICKED, None)
    if fired:
        _fail("deleted callback was invoked")
    print("OK: callback deletion")


def test_object_lifetime_and_pointer_validation(lv):
    btn = _widget_type(lv, "button")(lv.screen_active())
    btn.delete()
    try:
        btn.get_width()
    except lv.LvReferenceError:
        pass
    else:
        _fail("deleted object did not raise LvReferenceError")

    try:
        _widget_type(lv, "label")("not an LVGL parent")
    except (TypeError, ValueError, SyntaxError):
        pass
    else:
        _fail("invalid object pointer was accepted")
    print("OK: deleted-object and pointer validation")


def test_target_exceptions(lv):
    # LV_USE_TJPGD is 0 on every target: the JPEG decoder is jpegio's,
    # registered via lv_image_decoder_create by displayif, lvgl-circuitpython
    # and lvgl-python, so tjpgd_init/deinit exist nowhere.
    has_init = hasattr(lv, "tjpgd_init")
    has_deinit = hasattr(lv, "tjpgd_deinit")
    if has_init or has_deinit:
        _fail("TJPGD API leaked into a target that excludes the subsystem")
    print("OK: reviewed target exception policy")


def main():
    lv = _import_lv()

    test_import_and_constants(lv)
    test_string_constants(lv)
    test_enums(lv)
    test_enum_dir(lv)
    test_module_types(lv)
    test_struct_helpers(lv)
    test_widget_types(lv)
    test_module_functions(lv)
    test_target_exceptions(lv)

    if _is_initialized(lv):
        lv.deinit()

    test_basic(lv)
    disp, buf = _setup_display(lv)
    try:
        if _is_cpython():
            test_refr_now(lv, disp)
            test_pointer_buffer_dereference(lv, disp)
        test_widget(lv)
        test_struct_fields_and_arrays(lv)
        test_line_points_list_and_buffer(lv)
        test_struct_array_fields(lv)
        test_grad_helpers(lv)
        test_struct_dir(lv)
        test_struct_methods_by_value(lv)
        test_struct_value_from_dict(lv)
        test_event_callback(lv)
        test_callback_gc_with_widget_ref(lv)
        test_callback_gc_without_widget_ref(lv)
        test_button_callback(lv)
        test_callback_deletion(lv)
        test_object_lifetime_and_pointer_validation(lv)
        test_remove_style_none(lv)
        test_multi_callbacks(lv)
    finally:
        _teardown_display(buf)
        disp = None
        buf = None
        gc.collect()
        lv.deinit()

    print("All LVGL smoke tests passed.")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except SystemExit:
        raise
    except Exception as exc:
        print("FAIL: {}".format(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    if code != 0:
        raise SystemExit(code)
    if _is_cpython() and sys.platform == "win32":
        import os

        os._exit(0)
    raise SystemExit(0)
