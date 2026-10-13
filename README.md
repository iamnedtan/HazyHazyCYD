# HazyHazyCYD

Home Assistant wall panel on a Cheap Yellow Display (ESP32-2432S028R, dual-USB version), running [openHASP](https://www.openhasp.com).

The device only draws pages and reports touches over MQTT. All data and logic live in Home Assistant.

| Page | Content |
|------|---------|
| 0 | Overlay on every page: left/right edge strips switch pages |
| 1 | Haze, West region: PM2.5 (1h) on top, PSI (24h) below, coloured by NEA band |
| 2 | 6 buttons. Labels and actions configured in HA, no reflash |
| 3 | House status, 6 rows (placeholder entities for now) |

## Repo layout

```
pages/pages.jsonl          Screen layout, uploaded to the device
ha/packages/hazy_psi.yaml  PM2.5 + PSI sensors from data.gov.sg, band/colour templates
ha/packages/hazy_cyd.yaml  Button helpers + openHASP object bindings
```

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
3. Copy both files from `ha/packages/` into `/config/packages/`.
4. Restart HA.
5. Set the button labels: *Settings > Devices & Services > Helpers*, edit `CYD Button N Label`.

### 4. Make the buttons do something

Each screen button presses `input_button.cyd_btn_N`. Hook an automation to it:

```yaml
automation:
  - alias: CYD button 1 - toggle air purifier
    triggers:
      - trigger: state
        entity_id: input_button.cyd_btn_1
    actions:
      - action: fan.toggle
        target: { entity_id: fan.air_purifier }
```

Renaming the label and changing the automation both happen in HA. The device never needs a reflash.

## Status page placeholders

`ha/packages/hazy_cyd.yaml` page 3 uses these placeholder IDs. Replace them with your own:

- `sensor.living_room_temperature`
- `sensor.living_room_humidity`
- `binary_sensor.front_door`
- `binary_sensor.windows` (for example a group of window sensors)
- `sensor.house_power`

"Lights on" counts every `light.*` entity that is on and needs no changes.

## Haze bands

| PM2.5 1h (µg/m³) | Band | | PSI 24h | Band |
|---|---|---|---|---|
| 0-55 | Normal (green) | | 0-50 | Good (green) |
| 56-150 | Elevated (yellow) | | 51-100 | Moderate (yellow) |
| 151-250 | High (orange) | | 101-200 | Unhealthy (orange) |
| >250 | Very High (red) | | 201-300 | Very Unhealthy (red) |
| | | | >300 | Hazardous (purple) |

To change region, replace `west` in `ha/packages/hazy_psi.yaml` with `north`, `south`, `east` or `central`.

## Notes and limits

- Screen is 320x240. The edge strips are 40px each, so page content is 240x240.
- Built-in fonts are 12, 16, 24 and 32 only. The CYD has no PSRAM, so openHASP's TrueType fonts (any size) are not usable. The haze numbers use 32.
- Touch is resistive (XPT2046). Keep buttons at least about 60x60px.
- To change the layout, edit `pages.jsonl` in the device's web file editor. Object IDs (`pXbY`) must match the bindings in `hazy_cyd.yaml`.
