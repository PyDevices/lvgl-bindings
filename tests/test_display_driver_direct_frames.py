"""A direct-framebuffer panel presents once a frame, however many areas.

On a DIRECT panel LVGL paints the panel's own buffer and calls the flush
callback once per dirty area. ``_flush_cb_direct`` hands every area to the
panel's ``flush_rect`` and, on the frame's last area, either calls ``show()``
(when ``flush_rect`` could not sync the area) or ``frame_done()`` (when it
could). Both are one present, and ``presents`` counts them, so a displaydev
panel's ``measure_fps`` frame count matches ``presents`` rather than the
number of flushes.

The test runs the real ``DisplayDriver._flush_cb_direct`` against stand-in
panels; like the other display_driver tests it extracts the class source,
because importing the module needs a live ``appdev.App``.
"""
from __future__ import annotations

import ast
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DISPLAY_DRIVER = REPO_ROOT / "python" / "display_driver.py"


def _load_display_driver_class():
    source = DISPLAY_DRIVER.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(DISPLAY_DRIVER))
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "DisplayDriver"
    )
    class_source = ast.get_source_segment(source, class_node)
    lv = types.SimpleNamespace(COLOR_FORMAT=types.SimpleNamespace(RGB565=0))
    namespace = {"lv": lv, "sys": sys}
    exec(compile(class_source, str(DISPLAY_DRIVER), "exec"), namespace)
    return namespace["DisplayDriver"]


class _LvDisplay:
    """The slice of ``lv.display`` the direct flush uses."""

    def __init__(self):
        self.last = False
        self.ready = 0

    def flush_is_last(self):
        return self.last

    def flush_ready(self):
        self.ready += 1


class _Area:
    def __init__(self, x1, y1, x2, y2):
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2


class _Panel:
    def __init__(self, synced, has_frame_done=True):
        self.synced = synced
        self.flushes = 0
        self.shows = 0
        self.frames_done = 0
        if not has_frame_done:
            self.frame_done = None

    def flush_rect(self, x, y, w, h):
        self.flushes += 1
        return self.synced

    def show(self):
        self.shows += 1

    def frame_done(self):
        self.frames_done += 1


def _drive(panel, frames=3, areas=4):
    cls = _load_display_driver_class()
    drv = cls.__new__(cls)
    drv.display_drv = panel
    drv.lv_display = _LvDisplay()
    drv._blocking = True
    drv.presents = 0
    for _ in range(frames):
        for i in range(areas):
            drv.lv_display.last = i == areas - 1
            drv._flush_cb_direct(None, _Area(0, i * 10, 99, i * 10 + 9), None)
    return drv


def test_a_synced_panel_reports_each_frame_once():
    panel = _Panel(synced=True)
    drv = _drive(panel)
    assert panel.flushes == 12
    assert panel.shows == 0
    assert panel.frames_done == 3
    assert drv.presents == 3
    assert drv.lv_display.ready == 12


def test_an_unsynced_panel_is_shown_once_a_frame():
    panel = _Panel(synced=False)
    drv = _drive(panel)
    assert panel.flushes == 12
    assert panel.shows == 3
    assert panel.frames_done == 0
    assert drv.presents == 3


def test_a_panel_without_frame_done_still_presents():
    """An older displaydev has no frame_done: nothing breaks."""
    panel = _Panel(synced=True, has_frame_done=False)
    drv = _drive(panel)
    assert panel.shows == 0
    assert drv.presents == 3
