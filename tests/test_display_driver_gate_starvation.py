"""The LVGL loop must leave the application time to run.

``event_loop`` runs ``lv.timer_handler()`` from one ``multimer`` ONE_SHOT
timer and re-arms it to what LVGL asked for (``_next_delay``). The overrun
branch is the interesting one: when a pass takes longer than the tick
period, the choice of when the next pass may start decides how much of the
thread the application gets -- on MicroPython the pass runs *between the
application's bytecodes, on the application's own thread*.

Resuming the instant a slow pass ends (the pre-fix behaviour) started
another full pass immediately and the application never got the processor.
Measured on an ESP32-P4 with a 720x720 MIPI-DSI panel: a 696x240 animated
bar (~67.8 ms a pass against a 10 ms tick) made a 300-iteration Python loop
take 20 340 ms and ``time.sleep_ms(5)`` take 52-77 ms -- LVGL held ~87 % of
the thread indefinitely (lvgl-bindings#15). Holding for the whole pass again
then doubled every UI stall on an ESP32-S3, so the hold is capped
(lvgl-bindings#19).

The test runs the real ``event_loop._on_timer`` against a virtual clock and
a ``timer_handler`` that costs 60 ms under a 10 ms tick, and asserts the
application still gets a floor of the wall time. The model is calibrated
against the board run: with the hold removed it reports LVGL holding ~87 %
of the thread, which is what the issue measured.
"""
from __future__ import annotations

import ast
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DISPLAY_DRIVER = REPO_ROOT / "python" / "display_driver.py"


class _Clock:
    """A virtual ``ticks_ms`` the test advances by hand."""

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


class _FakeTimer:
    """The slice of ``multimer.Timer`` the loop uses, on the virtual clock."""

    ONE_SHOT = 0
    PERIODIC = 1

    def __init__(self, clock):
        self._clock = clock
        self.name = None
        self.running = False
        self.due = None
        self.callback = None

    def init(self, *, mode=PERIODIC, freq=-1, period=-1, callback=None, hard=False):
        self.running = True
        self.callback = callback
        self.due = self._clock.now + period

    def deinit(self):
        self.running = False
        self.due = None

    def reschedule(self, delay_ms):
        self.due = self._clock.now + max(0, int(delay_ms))


def _fake_multimer(clock):
    mod = types.SimpleNamespace()
    mod.Timer = lambda _id=-1: _FakeTimer(clock)
    mod.Timer.ONE_SHOT = 0
    mod.Timer.PERIODIC = 1
    return mod


def _load_event_loop_class(lv_module, clock):
    """Exec just the real ``event_loop`` class body against a virtual clock.

    Same extraction as ``test_display_driver_nesting_integration`` -- the
    full module needs a live ``appdev.App`` at import time, which is
    orthogonal to the pacing rule.
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
        "multimer": _fake_multimer(clock),
        "ticks_ms": clock.ticks_ms,
        "ticks_diff": clock.ticks_diff,
        "LVGL_PERIOD_MS": 10,
        "LVGL_REFR_PERIOD_MS": 33,
        "_LV_NESTING": None,
    }
    exec(compile(class_source, str(DISPLAY_DRIVER), "exec"), namespace)
    return namespace["event_loop"]


def _mock_lv(clock, work_ms, wanted=0):
    """An ``lv`` whose ``timer_handler`` costs ``work_ms`` and says a timer is
    due again in ``wanted`` ms (0: at once, the animating case)."""
    mock = types.SimpleNamespace()
    calls = {"timer_handler": 0}

    def timer_handler():
        calls["timer_handler"] += 1
        clock.now += work_ms
        return wanted

    mock.timer_handler = timer_handler
    mock.tick_inc = lambda ms: None
    mock.is_initialized = lambda: True
    mock.init = lambda: None
    return mock, calls


def _run(period_ms, work_ms, horizon_ms, **kwargs):
    """Drive the real loop over ``horizon_ms`` of virtual wall time.

    The model is the board's: the timer's callback is delivered on the
    application's thread the instant it is due. Every millisecond the timer
    is not due is a millisecond the application got.
    """
    clock = _Clock()
    lv_mock, calls = _mock_lv(clock, work_ms)
    event_loop = _load_event_loop_class(lv_mock, clock)
    loop = event_loop(period_ms=period_ms, **kwargs)
    loop.enable()  # clear the constructor's initial pause: arms the timer
    timer = loop.timer

    app_ms = 0
    while clock.now < horizon_ms:
        if timer.running and clock.now >= timer.due:
            loop._on_timer(timer)
        else:
            clock.now += 1
            app_ms += 1
    return app_ms, calls["timer_handler"], clock.now


def test_slow_pass_leaves_the_application_a_share_of_the_thread():
    period_ms, work_ms, horizon = 10, 60, 1000
    app_ms, passes, elapsed = _run(period_ms, work_ms, horizon)

    assert passes > 0, "the loop never let LVGL run at all"
    share = app_ms / elapsed
    assert share >= 0.4, (
        "a %d ms LVGL pass under a %d ms tick left the application %.1f%% of "
        "the thread (%d of %d ms). After an overrun _next_delay has to hold "
        "the loop off for as long as the pass itself took, so a slow frame "
        "lowers the frame rate instead of taking the thread. See "
        "lvgl-bindings#15." % (work_ms, period_ms, 100 * share, app_ms, elapsed)
    )


def test_the_model_reproduces_the_board_without_the_hold():
    """Calibration: with the yield removed, LVGL takes ~87 % of the thread,
    the figure lvgl-bindings#15 measured. A model that cannot fail cannot
    prove anything."""
    period_ms, work_ms, horizon = 10, 68, 1000
    app_ms, passes, elapsed = _run(period_ms, work_ms, horizon, max_yield_ms=0)
    share = app_ms / elapsed
    assert share < 0.2, "the model no longer reproduces the starvation: %.1f%%" % (100 * share)


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


def test_the_loop_runs_when_lvgl_asks_not_on_a_poll():
    """LVGL saying "nothing for 33 ms" means one pass per 33 ms, not per 10."""
    clock = _Clock()
    lv_mock, calls = _mock_lv(clock, 1, wanted=33)
    event_loop = _load_event_loop_class(lv_mock, clock)
    loop = event_loop(period_ms=100)  # the bound is above LVGL's ask here
    loop.enable()
    timer = loop.timer
    while clock.now < 1000:
        if timer.running and clock.now >= timer.due:
            loop._on_timer(timer)
        else:
            clock.now += 1
    assert 27 <= calls["timer_handler"] <= 31, calls


def _hold_after_one_pass(work_ms, **kwargs):
    """How long the loop stays off after one overrunning pass."""
    clock = _Clock()
    lv_mock, _calls = _mock_lv(clock, work_ms)
    event_loop = _load_event_loop_class(lv_mock, clock)
    loop = event_loop(period_ms=10, **kwargs)
    loop.enable()
    timer = loop.timer
    clock.now = timer.due
    loop._on_timer(timer)  # this pass overruns by work_ms
    return timer.due - clock.now


def test_long_pass_holds_no_longer_than_max_yield():
    """A pass far longer than a repaint is the application's own work, run
    from LVGL timers. Holding for all of it again leaves the thread idle and
    doubles the stall; the hold is capped at ``max_yield_ms``.
    """
    assert _hold_after_one_pass(60) == 60  # lvgl-bindings#15's case: unchanged
    assert _hold_after_one_pass(500) == 100
    assert _hold_after_one_pass(500, max_yield_ms=30) == 30
    assert _hold_after_one_pass(500, max_yield_ms=0) == 10  # never under a period
