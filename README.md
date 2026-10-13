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

1. Open the openHASP web installer in Chrome or Edge: <https://install.openhasp.com> (if the CYD builds are missing there, use the nightly installer <https://nightly.openhasp.com>).
2. Pick the firmware build `esp32-2432s028r-st7789_4MB`.
3. Hold **BOOT** on the board, plug in USB, release BOOT, then flash.
4. If the screen stays blank, shows inverted colours or is mirrored, flash `esp32-2432s028r_v2_4MB` instead.
   Do not use `esp32-2432s028r_4MB`; that build is for the single-USB board.

### 2. Configure the device

1. On first boot the device starts a temporary Wi-Fi access point and shows a QR code. Connect to it (or use the touchscreen) and enter your Wi-Fi details.
2. Open `http://<device-ip>` in a browser.
3. **Settings > MQTT**: broker = HA IP, port 1883, user/password = a dedicated HA user (for example `cyd`), **Plate name = `hazycyd`**.
4. **Settings > Display**: orientation landscape (90° or 270°, whichever is upright), set idle dim/off times.
5. Calibrate touch if taps land in the wrong place.
6. **File Editor**: upload `pages/pages.jsonl`, then reboot.

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
