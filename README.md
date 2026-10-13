# HazyHazyCYD

Home Assistant wall panel on a Cheap Yellow Display (ESP32-2432S028R, dual-USB version), running [openHASP](https://www.openhasp.com).

The device only draws pages and reports touches over MQTT. All data and logic live in Home Assistant.
Look: [Mecha Armor UI](https://claude.ai/artifact/X4594PmkBQB1hCrwdjFbVm), "Armor Plate" (light) draft.

| Page | Content |
|------|---------|
| 0 | Overlay on every page: left/right edge rails switch pages (wraps around) |
| 1 | Jurong West: NEA 2-hour forecast + home weather (left), PM2.5 1h and PSI 24h with NEA bands (right) |
| 2 | Living room: 8 buttons (AC 25/26, Low AC fan modes, Main Light, Dining/Prism fan, Off AC) |
| 3 | Ceiling fans: dining table and prism fan IR controls |
| 4 | KX camera thumbnail, refreshed every 10 s while shown |
| 5 | MK camera thumbnail, refreshed every 10 s while shown |

## Repo layout

```
tools/gen_panel.py             Generator: edit this, then run it
pages/pages.jsonl              GENERATED screen layout, uploaded to the device
ha/packages/hazy_cyd.yaml      GENERATED button helpers + openHASP object bindings
ha/packages/hazy_psi.yaml      PM2.5, PSI, NEA forecast sensors and band colours
ha/packages/hazy_routines.yaml Night screen schedule (off 00:00-06:00, dim-only by day)
ha/packages/hazy_cameras.yaml  Fresh-frame RTSP snapshot cameras + thumbnail refresh
```

## Changing the layout

1. Edit the CONFIG section of `tools/gen_panel.py` (buttons, fan controls, entities).
2. Run `python3 tools/gen_panel.py`.
3. Upload `pages/pages.jsonl` to the plate and reboot:
   ```bash
   curl -F "data=@pages/pages.jsonl;filename=/pages.jsonl" http://192.168.100.167/edit
   curl http://192.168.100.167/reboot
   ```
4. Copy `ha/packages/hazy_cyd.yaml` to HA and reload the openHASP integration (restart HA if helpers changed).

Object ids are allocated in fixed blocks per section, so a change inside one section does not shift the bindings of others.

## Setup

### 1. Flash the firmware

Tested on this board (dual-USB, ESP32-D0WD-V3) with openHASP **0.7.0-rc13**, build `esp32-2432s028r_4MB` (ILI9341 driver).
Colours and orientation are correct with this build. No ST7789 build exists in the 0.7.0-rc13 release.

From the command line:

1. Download `sunton.zip` from the [0.7.0-rc13 release](https://github.com/HASwitchPlate/openHASP/releases/tag/0.7.0-rc13) and extract
   `esp32-2432s028r_full_4MB_v0.7.0-rc13_042fe05.bin`.
2. Install esptool: `python3 -m venv .venv && .venv/bin/pip install esptool`.
3. Flash:
   ```bash
   .venv/bin/esptool --port /dev/ttyUSB0 erase-flash
   .venv/bin/esptool --port /dev/ttyUSB0 --baud 921600 write-flash 0x0 esp32-2432s028r_full_4MB_v0.7.0-rc13_042fe05.bin
   ```

Alternatively use the web installer in Chrome: <https://nightly.openhasp.com>, board "Sunton 2432S028R".

On Linux your user must be in the `dialout` group to open `/dev/ttyUSB0`.
If flashing fails with `Failed to connect`, hold BOOT, tap RST, release BOOT and retry.

### 2. Configure the device

1. On first boot the device starts a temporary access point `HASP-xxxxxx` (password `haspadmin`) and shows a QR code.
   Connect to it and enter your Wi-Fi details at `http://192.168.4.1`.
2. **Touch does not work until it is calibrated.** Send `calibrate` on the serial console (115200 baud) and tap each target.
   The calibration is saved to the device config.
3. Open `http://<device-ip>`, **Configuration > MQTT Settings**:
   - Hostname: `hazycyd` (this is the plate name and MQTT topic, not the broker)
   - Broker Server Name: HA IP address, port `1883`
   - Username / password: a dedicated HA user
4. Set landscape rotation: `rotate` = `1` (Configuration > Display, or POST `{"rotate":1}` to `/api/config/gui/`).
5. Upload `pages/pages.jsonl` with the File Editor (or `curl -F "data=@pages/pages.jsonl;filename=/pages.jsonl" http://<device-ip>/edit`), then reboot (`http://<device-ip>/reboot`).
6. Check `http://<device-ip>/api/info/`: MQTT status should be `Connected`.

### 3. Home Assistant

1. Install **openHASP** from HACS (custom component), restart HA. The plate appears under *Devices & Services* via MQTT discovery; add it.
2. Enable packages in `configuration.yaml` if not already:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
3. Copy all files from `ha/packages/` into `/config/packages/`.
4. Restart HA.
5. Optional: override a page 2 button live with the helpers `CYD Button N Label` / `CYD Button N Entity`.

## Haze bands

| PM2.5 1h (µg/m³) | Band | | PSI 24h | Band |
|---|---|---|---|---|
| 0-55 | Normal (grey tag) | | 0-50 | Good (grey tag) |
| 56-150 | Elevated (caution-yellow) | | 51-100 | Moderate (caution-yellow) |
| 151-250 | High (warning-red) | | 101-200 | Unhealthy (warning-red) |
| >250 | Very High (system-red) | | 201-300 | Very Unhealthy (system-red) |
| | | | >300 | Hazardous (black, yellow text) |

To change region, replace `west` in `ha/packages/hazy_psi.yaml` with `north`, `south`, `east` or `central`.

## Notes and limits

- Screen is 320x240. The edge rails are 40px each; page content is x 44-276.
- Built-in fonts are 12, 16, 24 and 32 only. The CYD has no PSRAM, so openHASP's TrueType fonts (any size) are not usable. The haze numbers use 32.
- Touch is resistive (XPT2046). Keep buttons large; the fan page's 74x42 buttons are the practical minimum.
- No PSRAM: about 17 KB of LVGL memory is left with the current pages. Check `http://<device-ip>/api/info/` after changes.
- openHASP cannot clip shapes. Cut corners are thick lines in the background colour laid over each corner.
- The default theme adds a gradient to fills; the generator sets `bg_grad_dir: 0` on everything.
- Camera thumbnails are 112x63 drawn at 2x. Larger frames (e.g. 154x86, 26 KB) fail with
  `img buffer creation failed` and crash the plate. RTSP URLs live in HA `secrets.yaml`
  (`cyd_kx_rtsp`, `cyd_mk_rtsp`), never in this repo. The TP-Link `live_view` cameras cache
  their snapshot for 5 minutes, hence the separate ffmpeg cameras.
- Plate log: `telnet <device-ip>` (no login) shows MQTT commands and errors live.
- Screen dims after 60 s idle and never turns off, except 00:00-06:00 (`hazy_routines.yaml`).
