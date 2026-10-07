# Hand-written Python helpers

Pure-Python modules that ship with the LVGL bindings. These are **not**
generator output — edit them here, then sync into consumer repos.

| File | Import | Notes |
|------|--------|-------|
| `fs_driver.py` | `import fs_driver` | Python-backed `lv_fs` driver: `fs_driver.register("S")`, then `lv.binfont_create("S:fonts/x.bin")` streams from the platform filesystem. Pairs with the runtime-loadable fonts in [`../fonts/`](../fonts/) |

`display_driver.py`, the coordinator that wires LVGL to a PyDevices
`board_config`, lives in
[PyDevices/pydevices `lib/`](https://github.com/PyDevices/pydevices/blob/main/lib/display_driver.py)
and ships with `pydevices`, beside the `appdev`, `events`, `keys` and `multimer`
it needs. It was here until 2026-10.

## Sync into consumers

| Repo | Destination | How it ships |
|------|-------------|--------------|
| [lvgl-micropython](https://github.com/PyDevices/lvgl-micropython) | `lib/fs_driver.py` | Frozen via `manifest.py` |
| [lvgl-circuitpython](https://github.com/PyDevices/lvgl-circuitpython) | `lib/fs_driver.py` | Frozen via `manifest.py` (unix builds) |
| [lvgl-python](https://github.com/PyDevices/lvgl-python) | repo root | `py_modules` in the `pydevices-lvgl` wheel |

Each consumer has `scripts/sync_from_lvgl_bindings.sh` (or extends the CPython
one) that copies this file from **PyDevices/lvgl-bindings on GitHub**.

## MIP (optional)

```text
mip.install("github:PyDevices/lvgl-bindings/packages/fs_driver.json")
```

`display_driver` comes with `mip.install("pydevices", index="https://PyDevices.github.io/mip")`.
