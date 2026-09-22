"""The event-loop gate must leave the application time to run.

``event_loop._arm_gate`` paces ``lv.task_handler()`` from the *previous*
slot rather than from completion, because pacing from completion halved the
tick rate. The overrun branch is the interesting one: when a pass takes
longer than the tick period, the gate has to decide when the next pass may
start, and on MicroPython that decision is what decides how much of the
thread the application gets -- the tick arrives through
``micropython.schedule``, so ``task_handler`` runs *between the
application's bytecodes, on the application's own thread*.

Resynchronising the gate to *now* (the pre-fix behaviour) opens it at the
instant the slow pass ends, so the tick that was queued while it ran starts
another full pass immediately and the application never gets the processor.
Measured on an ESP32-P4 with a 720x720 MIPI-DSI panel: a 696x240 animated
bar (~67.8 ms a pass against a 10 ms tick) made a 300-iteration Python loop
take 20 340 ms and ``time.sleep_ms(5)`` take 52-77 ms -- LVGL held ~87 % of
the thread indefinitely (lvgl-bindings#15).

The test runs the real ``event_loop.timer_cb`` against a virtual clock and a
``task_handler`` that costs 60 ms under a 10 ms tick, and asserts the
application still gets a floor of the wall time.

The model is calibrated against that board run: at a 68 ms pass it reports
LVGL holding 87.2 % of the thread, which is the ~87 % the issue measured.
That calibration also refutes the first fix the issue proposes -- setting
the next slot to ``now + delay`` changes nothing, because the timer's own
cadence already delivers the next tick a full period after the pass ends,
and that period *is* the 10 ms the application was already getting. Only a
bound proportional to the work just done moves the number.
"""
from __future__ import annotations

import ast
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DISPLAY_DRIVER = REPO_ROOT / "python" / "display_driver.py"


class _Clock:
    """A virtual ``ticks_ms`` the test advances by hand.

    ``ticks_*`` are the MicroPython wrapping-arithmetic helpers; plain
    integer arithmetic is a faithful stand-in over the horizons used here.
    """

    def __init__(self):
        self.now = 0

    def ticks_ms(self):
        return self.now

    @staticmethod
    def ticks_add(t, delta):
        return t + delta

    @staticmethod
    def ticks_diff(a, b):
        return a - b


class _Subscription:
    def cancel(self):
        pass


class _App:
    """The slice of ``appdev.App`` the sync path touches.

    ``enable()`` subscribes the tick through ``app.every``; the subscription
    is never delivered here because the test calls ``timer_cb`` itself, which
    is what lets it control the clock.
    """

    _timer = object()

    def every(self, _ms, _cb):
        return _Subscription()

    def on_start(self, _cb):
        pass


def _load_event_loop_class(lv_module, clock):
    """Exec just the real ``event_loop`` class body against a virtual clock.

    Same extraction as ``test_display_driver_nesting_integration`` -- the
    full module needs a live ``appdev.App`` at import time, which is
    orthogonal to the gate.
    """
    source = DISPLAY_DRIVER.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(DISPLAY_DRIVER))
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "event_loop"
    )
    class_source = ast.get_source_segment(source, class_node)
    assert class_source, "could not extract the event_loop class source"

    namespace = {
        "lv": lv_module,
        "sys": sys,
        "asyncio_available": False,
        "asyncio": None,
        "ticks_ms": clock.ticks_ms,
        "ticks_add": clock.ticks_add,
        "ticks_diff": clock.ticks_diff,
        "app": _App(),
        "LVGL_PERIOD_MS": 10,
        "_LV_NESTING": None,
    }
    exec(compile(class_source, str(DISPLAY_DRIVER), "exec"), namespace)
    return namespace["event_loop"]


def _mock_lv(clock, work_ms):
    """An ``lv`` whose ``task_handler`` costs ``work_ms`` of virtual time."""
    mock = types.SimpleNamespace()
    calls = {"task_handler": 0}

    def task_handler():
        calls["task_handler"] += 1
        clock.now += work_ms

    mock.task_handler = task_handler
    mock.tick_inc = lambda ms: None
    mock.is_initialized = lambda: True
    mock.init = lambda: None
    return mock, calls


def _run(period_ms, work_ms, horizon_ms):
    """Drive the real ``timer_cb`` over ``horizon_ms`` of virtual wall time.

    The model is the board's: a periodic timer whose callback is delivered on
    the application's thread. While a slow pass runs, whole periods elapse and
    the tick that comes due is delivered as soon as the pass returns (the
    ``micropython.schedule`` backlog) -- so a gate that is already open at
    that instant starts the next pass with no application time in between.
    Every millisecond the timer is not due, or the gate rejects it, is a
    millisecond the application got.
    """
    clock = _Clock()
    lv_mock, calls = _mock_lv(clock, work_ms)
    event_loop = _load_event_loop_class(lv_mock, clock)
    loop = event_loop(period_ms=period_ms)
    loop.enable()  # clear the constructor's initial pause

    app_ms = 0
    next_due = period_ms
    while clock.now < horizon_ms:
        if clock.now >= next_due:
            loop.timer_cb(None)
            # Re-arm from now: a periodic timer that fell behind during a
            # long callback comes due again immediately, not six times.
            next_due = clock.now + period_ms
        else:
            clock.now += 1
            app_ms += 1
    return app_ms, calls["task_handler"], clock.now


def test_slow_pass_leaves_the_application_a_share_of_the_thread():
    period_ms, work_ms, horizon = 10, 60, 1000
    app_ms, passes, elapsed = _run(period_ms, work_ms, horizon)

    assert passes > 0, "the gate never let LVGL run at all"
    share = app_ms / elapsed
    assert share >= 0.4, (
        "a %d ms LVGL pass under a %d ms tick left the application %.1f%% of "
        "the thread (%d of %d ms). After an overrun event_loop._arm_gate has "
        "to hold the gate shut for as long as the pass itself took, so a slow "
        "frame lowers the frame rate instead of taking the thread. Resyncing "
        "to now -- or to now + delay, which the timer's cadence already gives "
        "you -- leaves the application only the one tick period between "
        "passes. See lvgl-bindings#15."
        % (work_ms, period_ms, 100 * share, app_ms, elapsed)
    )


def test_fast_passes_keep_the_full_tick_cadence():
    """The control: the overrun branch must not slow down healthy frames.

    A 1 ms pass under a 10 ms tick should still run about once per period.
    Without this, a fix that simply throttles LVGL would pass the test above.
    """
    period_ms, work_ms, horizon = 10, 1, 1000
    app_ms, passes, elapsed = _run(period_ms, work_ms, horizon)

    expected = horizon // period_ms
    assert passes >= 0.9 * expected, (
        "fast frames lost their cadence: %d passes over %d ms at a %d ms "
        "tick, expected about %d" % (passes, elapsed, period_ms, expected)
    )
    assert app_ms / elapsed >= 0.8
