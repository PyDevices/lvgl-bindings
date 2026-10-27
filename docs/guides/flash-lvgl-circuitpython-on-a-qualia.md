# Flash LVGL CircuitPython on a Qualia

This guide builds a full-LVGL CircuitPython image for the Adafruit Qualia S3
RGB666 (`adafruit_qualia_s3_rgb666`) and flashes it, keeping Adafruit's TinyUF2
bootloader. The same steps apply to any 16 MB ESP32-S3 board whose stock app
partition is too small for LVGL.

## Build

[micropython-pydevices](https://github.com/PyDevices/micropython-pydevices)'
`build_mp.py` fetches CircuitPython, hands lvgl-circuitpython to its make as a
user C module, and runs the build. Two things go on the end of the command for
this board. `CIRCUITPY_GIFIO=0` stops CircuitPython's AnimatedGIF decoder
colliding with LVGL's. A partition table with a 4 MB app slot goes in through
`FLASH_SIZE_SDKCONFIG`, because the stock 16 MB table gives the app 2 MB and the
LVGL firmware is about 2.9 MB.

```bash
git clone https://github.com/PyDevices/micropython-pydevices
git clone https://github.com/PyDevices/lvgl-circuitpython
cd micropython-pydevices
LVCP="$(realpath ../lvgl-circuitpython)"
PARTS="$(pwd)/qualia-lvgl-partitions.defaults"
printf 'CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="%s"\nCONFIG_PARTITION_TABLE_FILENAME="%s"\n' \
    "$LVCP/scripts/partitions-16MB-lvgl.csv" "$LVCP/scripts/partitions-16MB-lvgl.csv" \
    > "$PARTS"
./build_mp.py --interpreter circuitpython --port espressif \
    --board adafruit_qualia_s3_rgb666 --modules "$LVCP" CIRCUITPY_GIFIO=0 \
    "FLASH_SIZE_SDKCONFIG=esp-idf-config/sdkconfig-flash-16MB.defaults;$PARTS"
```

The first build clones CircuitPython and ESP-IDF, so it needs the network and
takes a while. Later builds reuse them.

The output is in `builds/circuitpython/espressif/adafruit_qualia_s3_rgb666/`. A
board whose app slot already holds 3 MB or more needs only `CIRCUITPY_GIFIO=0`.

The partition path must be absolute. A relative path outside the port tree is
ignored by the IDF's config generator, and the build silently keeps the stock
2 MB table. Check the built config:

```bash
grep PARTITION_TABLE_FILENAME builds/circuitpython/espressif/adafruit_qualia_s3_rgb666/esp-idf/sdkconfig
```

It should name `partitions-16MB-lvgl.csv`. A good link reports about 2.9 MB used
(`2942608 bytes used` on CircuitPython 11.0.0-alpha.2) out of `4194304 bytes`. Without the right table the build ends
in `Too little flash!!!`.

`scripts/partitions-16MB-lvgl.csv` has `ota_0 = 4096K`; it moves `uf2` to
`0x610000` and shrinks `user_fs`.

### Build files

In `builds/circuitpython/espressif/adafruit_qualia_s3_rgb666/`:

| File | Role |
|------|------|
| `circuitpython-firmware.bin` | App image only (flash at `0x10000`) |
| `firmware.bin` | Joined IDF bootloader, partition table and app (esptool at `0x0`) |
| `firmware.uf2` | Starts at `0x0`, ready to copy onto `TFT_S3BOOT` |

`firmware.uf2` needs no conversion. Like Adafruit's official Qualia UF2s, it
starts at address `0x0`, which TinyUF2 maps into `ota_0`, with family
`0xc47e5767` (ESP32-S3).

## Other build errors

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `Argument list too long` in the qstr step | LVGL's hundreds of `.c` files in the qstr scan | Use `micropython.mk` as it is: it links LVGL through `SRC_USERMOD_LIB_C`, which the qstr scan never sees |
| `-Werror=suggest-attribute=format` on LVGL | Espressif's warning flags | `micropython.mk` already puts `-Wno-suggest-attribute=format` on the LVGL objects only |
| Duplicate `GIF_*` symbols at link | gifio and LVGL's gif | Put `CIRCUITPY_GIFIO=0` on the make line; on an existing build directory that had gifio on, run `rm -f build-<board>/genhdr/module/*gifio* build-<board>/genhdr/qstr/*gifio*` |
| `Too little flash` | The stock partition CSV is still selected | Add the `FLASH_SIZE_SDKCONFIG=` argument from Build |

## Flash

Do not flash the joined `firmware.bin` if you want Adafruit's TinyUF2. It
replaces the second-stage path with the IDF bootloader. Adafruit's documented
flow uses TinyUF2, and the stock TinyUF2 layout (`ota_0 = 2048K`) cannot hold a
2.9 MB LVGL app. The 4 MB table above is what makes room.

### Put the board in ROM download mode

From a running CircuitPython, no buttons are needed:

```python
import microcontroller
microcontroller.on_next_reset(microcontroller.RunMode.BOOTLOADER)
microcontroller.reset()
```

The board comes back as `303A:0009`, the S3's ROM USB port.

Without a running CircuitPython, use the buttons. On the Qualia, the buttons are a side stack: Reset (top), UP and DN. Boot0
sits between UP and the MCU, not between UP and DN.

```text
Hold Boot0 -> press and release Reset -> release Boot0
```

The board then shows USB ID `303A:1001`, usually on a new serial port. Other IDs
you may meet:

| VID:PID | Meaning |
|---------|---------|
| `303A:4001` | USB-Serial/JTAG while an app (such as MicroPython) runs |
| `303A:1001` | ROM download mode, entered with the buttons |
| `303A:0009` | ROM download mode, entered from CircuitPython |
| `239A:0147` | TinyUF2 CDC; volume `TFT_S3BOOT` |
| `239A:8148` | CircuitPython on the Qualia; volume `CIRCUITPY` |

`esptool --before usb-reset` while the app owns the port usually fails with
`Invalid head of packet (0x08)`, so enter ROM mode one of the two ways above.
`--after hard-reset` often leaves the chip in ROM; `--after watchdog-reset`
restarts it. esptool 5.x rejects `--flash-freq 120m`: use `80m` or `keep`.

### Write TinyUF2, the partition table and the app

Download the TinyUF2 0.35.0 zip for the Qualia from the
[tinyuf2 releases](https://github.com/adafruit/tinyuf2/releases) and take
`bootloader.bin`, `tinyuf2.bin` and `ota_data_initial.bin` from it. Make the
partition table binary from `partitions-16MB-lvgl.csv` with the IDF's
`gen_esp32part.py`. In ROM mode:

```bash
python -m esptool --chip esp32s3 -p <serial-port> --before no-reset --after watchdog-reset --baud 460800 \
  write-flash --flash-mode dio --flash-freq 80m --flash-size 16MB \
  0x0      bootloader.bin \
  0x8000   partition-table-lvgl.bin \
  0xe000   ota_data_initial.bin \
  0x10000  circuitpython-firmware.bin \
  0x610000 tinyuf2.bin
```

The board restarts into TinyUF2 by itself.

### Copy the UF2 once

`ota_data_initial.bin` from the TinyUF2 zip is all `0xFF`. With a `factory`
(uf2) partition present, the bootloader chooses TinyUF2 and shows `TFT_S3BOOT`,
even though `ota_0` already holds a valid app. With `TFT_S3BOOT` mounted, copy
the LVGL `.uf2` (address `0x0`) onto the drive. TinyUF2 programs `ota_0` and
updates `otadata`, and the board comes back as `CIRCUITPY` with `239A:8148`.

`INFO_UF2.TXT` on the drive shows `Flash Size: 0x00400000` when the LVGL table
is active. Stock TinyUF2 shows `0x00200000`.

## Verify

At the CircuitPython prompt:

```text
>>> import lvgl
>>> print(lvgl)
<module 'lvgl'>
```

## Back to stock

For a baseline without LVGL, put the board in ROM mode and flash TinyUF2's
`combined.bin` at `0x0` (`dio`, `80m`, `16MB`), press Reset to reach
`TFT_S3BOOT`, and copy Adafruit's official UF2 from
[circuitpython.org](https://circuitpython.org/board/adafruit_qualia_s3_rgb666/).
The official app is about 2 MB (1,957,712 bytes for 11.0.0-alpha.2), which
fits the stock 2 MB `ota_0`; LVGL adds about 1 MB to it.
