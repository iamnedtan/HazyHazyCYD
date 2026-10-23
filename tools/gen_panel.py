#!/usr/bin/env python3
"""Generate the openHASP layout and the matching Home Assistant bindings.

Look: Mecha Armor UI, "Armor Plate" (light) draft.

Outputs:
  pages/pages.jsonl          upload to the plate (File Editor), then reboot
  ha/packages/hazy_cyd.yaml  copy to /config/packages/, reload openHASP

Edit the CONFIG section, then run:  python3 tools/gen_panel.py
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- CONFIG ----
PLATE = "hazycyd"
REGION = "WEST"
PM_SENSOR = "sensor.haze_pm25_1h_west"
PM_BAND = "sensor.haze_pm25_1h_west_band"
PSI_SENSOR = "sensor.haze_psi_24h_west"
PSI_BAND = "sensor.haze_psi_24h_west_band"
UPDATED_SENSOR = "sensor.haze_updated"
AREA = "JURONG WEST"
PM_UPDATED = "sensor.haze_pm25_updated"                 # "11:00"
PSI_UPDATED = UPDATED_SENSOR                            # "11:00"
WX_FORECAST = "sensor.nea_forecast_jurong_west"         # NEA 2-hour forecast text
WX_UPDATED = "sensor.nea_forecast_jurong_west_updated"  # "11:06"
WX_UNTIL = "sensor.nea_forecast_jurong_west_until"      # "13:00"
WX_TEMP = "sensor.home_679_06_28_temperature"
WX_FEELS = "sensor.home_679_06_28_apparent_temperature"
WX_HUM = "sensor.home_679_06_28_humidity"
PM_SCALE = 250   # PM2.5 value that fills all 12 segments
PSI_SCALE = 300  # PSI value that fills all 12 segments

# Page 2 buttons, in grid order (left-right, top-bottom).
#   name:   default label. Override live in HA: input_text.cyd_btn_N_label
#   entity: default target, run with homeassistant.turn_on (scripts, scenes,
#           lights, switches...). Override live in HA: input_text.cyd_btn_N_entity
#   icon:   built-in MDI icon code (only the ~146 icons in openHASP's font)
#   icon_color: icon colour token
#   state:  optional entity; when "on" the button is drawn active (dark)
BUTTONS = [
    {"name": "AC 25", "entity": "script.living_study_ac_25",
     "icon": "\uE01B", "icon_color": "#626766", "state": None},   # air-conditioner
    {"name": "AC 26", "entity": "script.living_study_ac_26",
     "icon": "\uE01B", "icon_color": "#626766", "state": None},   # air-conditioner
    {"name": "Low AC Low Fan", "entity": "script.livrm_ac_26_ac_low_fan_low",
     "icon": "\uE717", "icon_color": "#626766", "state": None},   # snowflake
    {"name": "Low AC High Fan", "entity": "script.living_study_ac_26_fan_high",
     "icon": "\uE210", "icon_color": "#626766", "state": None},   # fan
    {"name": "Main Light", "entity": "script.rm4_lr_mainlight_toggle",
     "icon": "\uE769", "icon_color": "#626766", "state": None},   # ceiling-light
    {"name": "Dining Fan", "entity": "script.rm4_lr_dining_toggle",
     "icon": "\uE210", "icon_color": "#626766", "state": None},   # fan
    {"name": "Prism Fan", "entity": "script.rm4_lr_prism_main_toggle",
     "icon": "\uE210", "icon_color": "#626766", "state": None},   # fan
    {"name": "Off AC", "entity": "script.living_study_off",
     "icon": "\uE425", "icon_color": "#D82F25", "state": None},   # power, warning-red
]

# Page 3: ceiling fans. Each section: (title, buttons).
# IR scripts, run with homeassistant.turn_on. No on/off state is shown:
# IR gives no feedback, so the real fan state is unknown.
FAN_SECTIONS = [
    ("DINING TABLE", [
        {"name": "Main Switch", "entity": "script.rm4_lr_dining_toggle", "icon": "\uE425"},
        {"name": "Fan On/Off", "entity": "script.rm4_lr_dining_fan_toggle", "icon": "\uE210"},
        {"name": "Light On/Off", "entity": "script.rm4_lr_dining_light_toggle", "icon": "\uE95F"},
        {"name": "Fan 1", "entity": "script.rm4_lr_dining_fan1", "icon": "\uE210"},
        {"name": "Fan 3", "entity": "script.rm4_lr_dining_fan3", "icon": "\uE210"},
    ]),
    ("PRISM FAN", [
        {"name": "Main Switch", "entity": "script.rm4_lr_prism_main_toggle", "icon": "\uE425"},
        {"name": "Fan Off", "entity": "script.rm4_lr_prism_toggle_remote", "icon": "\uE210",
         "icon_color": "#D82F25"},
        {"name": "Light On", "entity": "script.rm4_lr_prism_on_light", "icon": "\uE6E8"},
        {"name": "Fan 1", "entity": "script.rm4_lr_prism_fan1", "icon": "\uE210"},
        {"name": "Fan 3", "entity": "script.rm4_lr_prism_fan3", "icon": "\uE210"},
        {"name": "Light Off", "entity": "script.rm4_lr_prism_off_light", "icon": "\uE335"},
    ]),
]

# Camera pages: one page each. The image is pushed by HA (ha/packages/hazy_cameras.yaml)
# at CAM_W x CAM_H and drawn at CAM_ZOOM/256 scale (no PSRAM: keep it small).
CAMERAS = [
    {"title": "KX CAMERA", "caption": "KX · TAPO C211", "entity": "camera.cyd_kx_snapshot"},
    {"title": "MK CAMERA", "caption": "MK · TAPO C211", "entity": "camera.cyd_mk_snapshot"},
]
CAM_W, CAM_H, CAM_ZOOM = 112, 63, 512
CAM_IMG_ID = 20
HA_URL = "http://192.168.100.193:8123"

# ---------------------------------------------------------------- TOKENS ----
# Mecha Armor UI tokens (exact values).
BACKGROUND = "#D9DAD6"
ARMOR_WHITE = "#E8E8E4"
ARMOR_LIGHT = "#F2F2EE"
ARMOR_GRAY = "#B7B9B7"
MACHINE_GRAY = "#777B7A"
DARK_ARMOR = "#292D2F"
BLACK_METAL = "#151719"
WARNING_RED = "#D82F25"
SYSTEM_RED = "#B8201B"
SIGNAL_GOLD = "#C99A3D"
CAUTION_YELLOW = "#D4A62A"
TEXT_PRIMARY = "#25282A"
TEXT_SECONDARY = "#626766"
LINE_LIGHT = "#C7C9C6"

CHAMFER_PANEL = 12
CHAMFER_BUTTON = 8
CHAMFER_CHIP = 6

# Screen geometry: 320x240 landscape, 40px edge rails, content x 44..276.
CX, CW = 44, 232

# ---------------------------------------------------------------- BUILD -----
lines = []         # pages.jsonl objects
bindings = []      # (obj, properties dict, event dict or None)
_next_id = {}


def add(page, obj, **props):
    """Append an object, auto-assigning its id. Returns 'pXbY'."""
    oid = props.pop("id", None)
    if oid is None:
        oid = _next_id.get(page, 1)
    _next_id[page] = max(_next_id.get(page, 1), oid + 1)
    o = {"page": page, "id": oid, "obj": obj}
    o.update(props)
    if "bg_color" in o:
        o.setdefault("bg_grad_dir", 0)   # the default theme adds a gradient
    lines.append(o)
    return f"p{page}b{oid}"


def id_block(page, base):
    """Start numbering at `base` so later edits inside one section never shift
    the object ids (and HA bindings) of other sections."""
    assert base >= _next_id.get(page, 1), f"id block {base} overlaps on page {page}"
    _next_id[page] = base


def bind(ref, properties=None, event=None):
    bindings.append((ref, properties or {}, event))


def label(page, x, y, w, h, text, font=12, color=TEXT_PRIMARY, align="left", **kw):
    return add(page, "label", x=x, y=y, w=w, h=h, text=text, text_font=font,
               text_color=color, align=align, click=0, **kw)


def chamfer(page, x, y, w, h, c, ground):
    """Cut the top-right and bottom-left corners of a rectangle.

    openHASP cannot clip shapes, so each cut is a thick line in the colour of
    whatever lies behind the rectangle, laid over the corner triangle.
    """
    width = math.ceil(c / math.sqrt(2)) + 1
    q = c / 4
    pad = width  # keep the line's thickness inside its own object
    corners = [
        # top-right corner at (x+w, y)
        ((x + w - 3 * q, y - q), (x + w + q, y + 3 * q)),
        # bottom-left corner at (x, y+h)
        ((x - q, y + h - 3 * q), (x + 3 * q, y + h + q)),
    ]
    for (x1, y1), (x2, y2) in corners:
        ox, oy = math.floor(min(x1, x2) - pad), math.floor(min(y1, y2) - pad)
        add(page, "line", x=ox, y=oy,
            points=[[round(x1 - ox), round(y1 - oy)], [round(x2 - ox), round(y2 - oy)]],
            line_width=width, line_color=ground, line_rounded=0, click=0)


def panel(page, x, y, w, h, fill=ARMOR_WHITE, ground=BACKGROUND):
    ref = add(page, "obj", x=x, y=y, w=w, h=h, radius=0, bg_color=fill, bg_opa=255,
              border_width=0, shadow_width=0, click=0)
    chamfer(page, x, y, w, h, CHAMFER_PANEL, ground)
    return ref


def page_base(page, title, index):
    add(page, "obj", x=0, y=0, w=320, h=240, radius=0, bg_color=BACKGROUND,
        bg_opa=255, border_width=0, click=0)
    label(page, CX, 4, 150, 22, title, font=16, text_letter_space=1)
    return label(page, CX + 100, 8, CW - 100, 16, index, font=12,
                 color=TEXT_SECONDARY, align="right", text_letter_space=1)


# Page 0: edge rails, drawn on top of every page ------------------------------
for oid, x, icon, word, side, action in [
    (1, 0, "", "PREV", 8, "page prev"),
    (2, 280, "", "NEXT", 4, "page next"),
]:
    add(0, "btn", id=oid, x=x, y=0, w=40, h=240, radius=0,
        bg_color=ARMOR_GRAY, bg_color02=MACHINE_GRAY, bg_grad_dir=0,
        border_side=side, border_width=1, border_color=MACHINE_GRAY,
        shadow_width=0, outline_width=0,
        text=icon, text_font=32, text_color=TEXT_PRIMARY, pad_bottom=16,
        value_str=word, value_font=12, value_color=TEXT_PRIMARY,
        value_letter_space=1, value_ofs_y=22,
        action={"up": action})


# Page 1: weather (left) + haze (right) ---------------------------------------
page_base(1, "", "P01")
clock = label(1, CX, 4, 52, 22, "--:--", font=16, text_letter_space=1)
bind(clock, {"text": '{{ now().strftime("%H:%M") }}'})   # HA re-renders every minute
label(1, CX + 54, 4, 120, 22, AREA, font=16, color=TEXT_SECONDARY, text_letter_space=1)

# NEA 2-hour forecast text -> built-in MDI weather icon.
WX_ICONS = [
    ("Thundery", "\uE67E"),   # weather-lightning-rainy
    ("Heavy", "\uE596"),      # weather-pouring
    ("Showers", "\uE597"),    # weather-rainy
    ("Rain", "\uE597"),       # weather-rainy
    ("Hazy", "\uEF30"),       # weather-hazy
    ("Mist", "\uE591"),       # weather-fog
    ("Fog", "\uE591"),        # weather-fog
    ("Windy", "\uE59D"),      # weather-windy
    ("Partly Cloudy (Night)", "\uEF31"),  # weather-night-partly-cloudy
    ("Partly Cloudy", "\uE595"),          # weather-partly-cloudy
    ("Cloudy", "\uE590"),     # weather-cloudy
    ("Night", "\uE594"),      # weather-night
    ("Fair", "\uE599"),       # weather-sunny
]


def weather_panel(page, x, y, w, h):
    panel(page, x, y, w, h)
    ix, iw = x + 8, w - 16
    label(page, ix, y + 4, iw, 16, "WEATHER · 2H", color=TEXT_SECONDARY, text_letter_space=1)
    icon = label(page, ix, y + 20, iw, 36, "\uE590", font=32)
    # "crop": wraps but never grows past its box (a "break" label grows taller
    # and overlaps the temperature). Long forecasts switch to the 12pt font.
    cond = label(page, ix, y + 58, iw, 38, "--", font=16, mode="crop")
    temp = label(page, ix, y + 98, iw, 38, "--", font=32)
    feels = label(page, ix, y + 138, iw, 16, "FEELS --", color=TEXT_SECONDARY, text_letter_space=1)
    hum = label(page, ix, y + 154, iw, 16, "HUM --", color=TEXT_SECONDARY, text_letter_space=1)
    upd = label(page, ix, y + 172, iw, 16, "", color=TEXT_SECONDARY, text_letter_space=1)
    till = label(page, ix, y + 188, iw, 16, "", color=TEXT_SECONDARY, text_letter_space=1)

    f = f'states("{WX_FORECAST}")'
    chain = "".join(f'{{% elif "{k}" in f %}}{v}' for k, v in WX_ICONS)[2:].replace(" elif", " if", 1)
    bind(icon, {"text": f'{{% set f = {f} %}}{{%{chain}{{% else %}}\uE590{{% endif %}}'})
    short = (f'{f} | replace(" (Day)", "") | replace(" (Night)", "")'
             f' | replace(" with Gusty Winds", " + WIND") | upper')
    # HA does the line breaking (panel "crop" labels do not wrap): about 11
    # characters per line fit at 16pt, 15 at 12pt. Use 16pt when the text fits
    # on 2 lines, else 12pt.
    fits16 = (f'(({short}) | wordwrap(11, break_long_words=false, wrapstring="\\n")).split("\\n")'
              f' | length <= 2 and ({short}).split(" ") | map("length") | max <= 11')
    bind(cond, {
        "text": (f'{{% if {fits16} %}}{{{{ ({short}) | wordwrap(11, break_long_words=false, wrapstring="\\n") }}}}'
                 f'{{% else %}}{{{{ ({short}) | wordwrap(15, break_long_words=false, wrapstring="\\n") }}}}{{% endif %}}'),
        "text_font": f'{{{{ 16 if {fits16} else 12 }}}}',
    })
    bind(temp, {"text": f'{{{{ states("{WX_TEMP}") | float(0) | round(1) }}}}°'})
    bind(feels, {"text": f'FEELS {{{{ states("{WX_FEELS}") | float(0) | round(1) }}}}°'})
    bind(hum, {"text": f'HUM {{{{ states("{WX_HUM}") | int(0) }}}}%'})
    bind(upd, {"text": f'UPD {{{{ states("{WX_UPDATED}") }}}}'})
    bind(till, {"text": f'TILL {{{{ states("{WX_UNTIL}") }}}}'})


def readout(page, x, y, w, caption, unit, sensor, band, scale, updated):
    panel(page, x, y, w, 102)
    ix, iw = x + 8, w - 16
    label(page, ix, y + 4, iw, 16, caption, color=TEXT_SECONDARY, text_letter_space=1)
    label(page, ix, y + 4, iw, 16, unit, color=TEXT_SECONDARY, align="right")
    # Value sits in a dark inset window (Mecha "display" panel), white digits.
    add(page, "obj", x=ix, y=y + 21, w=iw, h=36, radius=0, bg_color=DARK_ARMOR,
        bg_opa=255, border_width=0, shadow_width=0, click=0)
    value = label(page, ix + 6, y + 21, iw - 12, 36, "--", font=32, color=ARMOR_LIGHT)
    upd = label(page, ix + iw - 40, y + 38, 36, 16, "", color=ARMOR_GRAY, align="right")
    bind(upd, {"text": f'{{{{ states("{updated}") }}}}'})
    chip_y, chip_h = y + 60, 22
    chip = label(page, ix, chip_y, iw, chip_h, "", font=12, color=BLACK_METAL,
                 align="center", bg_opa=255, bg_color=ARMOR_GRAY, pad_top=4,
                 text_letter_space=1)
    chamfer(page, ix, chip_y, iw, chip_h, CHAMFER_CHIP, ARMOR_WHITE)
    seg_w, gap = 7, 1
    segs = []
    for i in range(12):
        segs.append(add(page, "obj", x=ix + i * (seg_w + gap), y=y + 88, w=seg_w, h=8,
                        radius=0, bg_color=LINE_LIGHT, bg_opa=255, border_width=0,
                        shadow_width=0, click=0))

    v = f'states("{sensor}")'
    bind(value, {"text": f'{{{{ {v} }}}}'})
    bind(chip, {
        "text": f'{{{{ states("{band}") | upper }}}}',
        "bg_color": f'{{{{ state_attr("{band}", "chip") }}}}',
        "text_color": f'{{{{ state_attr("{band}", "chip_text") }}}}',
    })
    for i, ref in enumerate(segs):
        threshold = round(i * scale / 12, 1)
        bind(ref, {"bg_color":
                   f'{{{{ "{DARK_ARMOR}" if {v} | float(0) > {threshold} else "{LINE_LIGHT}" }}}}'})


COL_W = (CW - 4) // 2          # two columns, 4px gap
id_block(1, 10)
weather_panel(1, CX, 30, COL_W, 208)
id_block(1, 30)
readout(1, CX + COL_W + 4, 30, COL_W, "PM2.5 1H", "µg/m³", PM_SENSOR, PM_BAND, PM_SCALE, PM_UPDATED)
id_block(1, 60)
readout(1, CX + COL_W + 4, 136, COL_W, "PSI 24H", "INDEX", PSI_SENSOR, PSI_BAND, PSI_SCALE, PSI_UPDATED)


# Page 2: buttons ------------------------------------------------------------
page_base(2, "LIVING ROOM", "P02")
bw, bh, gx, gy = 111, 48, 10, 5        # 2 columns x 4 rows
for n, cfg in enumerate(BUTTONS, start=1):
    id_block(2, n * 10)
    col, row = (n - 1) % 2, (n - 1) // 2
    x, y = CX + col * (bw + gx), 30 + row * (bh + gy)
    # The button is only the plate and the touch target. Text sits in separate
    # non-clickable labels on top (taps pass through to the button), because a
    # btn always centres its own text and cannot wrap it.
    btn = add(2, "btn", x=x, y=y, w=bw, h=bh, radius=0, text="",
              bg_color=ARMOR_WHITE, bg_color02=ARMOR_GRAY,
              border_width=0, outline_width=0, shadow_width=0, shadow_opa=0)
    if cfg["icon"]:
        label(2, x + 4, y + 11, 26, 26, cfg["icon"], font=24,
              color=cfg["icon_color"], align="center")
    one_line = len(cfg["name"]) <= 9          # labels cannot centre vertically
    name = label(2, x + 32, y + (14 if one_line else 5), bw - 36, 40,
                 cfg["name"].upper(), font=16, mode="break")
    chamfer(2, x, y, bw, bh, CHAMFER_BUTTON, BACKGROUND)
    lbl = f'states("input_text.cyd_btn_{n}_label")'
    name_props = {"text": f'{{{{ ({lbl} if {lbl} not in ["", "unknown", "unavailable"] else "{cfg["name"]}") | upper }}}}'}
    props = {}
    if cfg["state"]:
        on = f'is_state("{cfg["state"]}", "on")'
        props.update({
            "bg_color": f'{{{{ "{DARK_ARMOR}" if {on} else "{ARMOR_WHITE}" }}}}',
        })
        name_props["text_color"] = f'{{{{ "{ARMOR_LIGHT}" if {on} else "{TEXT_PRIMARY}" }}}}'
    bind(name, name_props)
    ent = f'states("input_text.cyd_btn_{n}_entity")'
    target = f'{{{{ {ent} if {ent} not in ["", "unknown", "unavailable"] else "{cfg["entity"]}" }}}}'
    bind(btn, props, {"up": [
        {"condition": f'{{{{ ({ent} not in ["", "unknown", "unavailable"]) or {bool(cfg["entity"])} }}}}'},
        {"service": "homeassistant.turn_on", "entity_id": target},
    ]})


# Page 3: living room ceiling fans ---------------------------------------------
page_base(3, "CEILING FANS", "P03")


def small_button(page, x, y, w, h, cfg):
    """Compact button: icon left, 2-line name right. No cut corners (memory)."""
    btn = add(page, "btn", x=x, y=y, w=w, h=h, radius=0, text="",
              bg_color=ARMOR_WHITE, bg_color02=ARMOR_GRAY, bg_grad_dir=0,
              border_width=0, outline_width=0, shadow_width=0, shadow_opa=0)
    label(page, x + 3, y + 9, 26, 26, cfg["icon"], font=24,
          color=cfg.get("icon_color", TEXT_SECONDARY), align="center")
    name = label(page, x + 30, y + 4, w - 32, h - 6, cfg["name"].upper(), font=12,
                 mode="break", text_letter_space=1)
    props = {}
    if cfg.get("state"):
        on = f'is_state("{cfg["state"]}", "on")'
        props["bg_color"] = f'{{{{ "{DARK_ARMOR}" if {on} else "{ARMOR_WHITE}" }}}}'
        bind(name, {"text_color": f'{{{{ "{ARMOR_LIGHT}" if {on} else "{TEXT_PRIMARY}" }}}}'})
    bind(btn, props, {"up": [{"service": "homeassistant.turn_on", "entity_id": cfg["entity"]}]})


sec_y = 28
for sec, (title, buttons) in enumerate(FAN_SECTIONS):
    id_block(3, 10 + sec * 50)
    label(3, CX, sec_y, CW, 14, title, color=TEXT_SECONDARY, text_letter_space=1)
    bw3, bh3, g3 = (CW - 8) // 3, 42, 4
    for i, cfg in enumerate(buttons):
        col, row = i % 3, i // 3
        small_button(3, CX + col * (bw3 + g3), sec_y + 15 + row * (bh3 + 3), bw3, bh3, cfg)
    sec_y += 15 + 2 * bh3 + 3 + 2


# Camera pages ---------------------------------------------------------------
for k, cam in enumerate(CAMERAS):
    pg = 4 + k
    page_base(pg, cam["title"], f"P{pg:02d}")
    id_block(pg, 10)
    win_y, win_h = 30, 208
    panel(pg, CX, win_y, CW, win_h, fill=BLACK_METAL)
    label(pg, CX + 10, win_y + 6, CW - 20, 16, cam["caption"], color=ARMOR_GRAY,
          text_letter_space=1)
    label(pg, CX + 10, win_y + win_h - 22, CW - 20, 16, "TAP IMAGE TO REFRESH",
          color=ARMOR_GRAY, align="right", text_letter_space=1)
    id_block(pg, CAM_IMG_ID)
    # Object is the source size, centred; zoom scales it around its centre.
    # auto_size must come before src: an empty src with auto_size on shrinks
    # the object to 0x0, and later images would then be invisible.
    img = add(pg, "img", auto_size=0, src="", x=CX + (CW - CAM_W) // 2,
              y=win_y + (win_h - CAM_H) // 2, w=CAM_W, h=CAM_H, zoom=CAM_ZOOM, click=1)
    pic = f'state_attr("{cam["entity"]}", "entity_picture")'
    bind(img, None, {"up": [{"service": "openhasp.push_image", "push": {
        "obj": img, "width": CAM_W, "height": CAM_H, "fitscreen": True,
        "image": f'{HA_URL}{{{{ {pic} }}}}'}}]})


# Wrap-around: NEXT on the last page goes to page 1, PREV on page 1 to the last.
LAST_PAGE = max(o["page"] for o in lines)
lines.append({"page": 1, "id": 0, "prev": LAST_PAGE})
lines.append({"page": LAST_PAGE, "id": 0, "next": 1})


# ---------------------------------------------------------------- WRITE -----
def write_jsonl():
    out = [json.dumps({"comment": "GENERATED by tools/gen_panel.py - edit the generator, not this file"})]
    page = None
    for o in lines:
        if o["page"] != page:
            page = o["page"]
            out.append(json.dumps({"page": page, "comment": f"---- page {page} ----"}))
        out.append(json.dumps(o, ensure_ascii=True, separators=(",", ":")))
    (ROOT / "pages" / "pages.jsonl").write_text("\n".join(out) + "\n")


def q(s):
    """YAML single-quoted scalar."""
    return "'" + str(s).replace("'", "''") + "'"


def write_yaml():
    y = []
    y.append("# GENERATED by tools/gen_panel.py - edit the generator, not this file.")
    y.append(f"# Plate name on the device must be \"{PLATE}\" (MQTT topic hasp/{PLATE}/...).")
    y.append("#")
    y.append("# Page 2 buttons:")
    y.append("#   - Rename a button: change input_text.cyd_btn_N_label in the HA UI. No reflash.")
    y.append("#     (No \"initial:\" on purpose - it would reset your label on every HA restart.")
    y.append("#      Empty label falls back to \"Button N\".)")
    y.append("#   - Change what a button runs: set input_text.cyd_btn_N_entity to an entity ID")
    y.append("#     (script.x, scene.x, light.x ...). It is run with homeassistant.turn_on.")
    y.append("#     Empty = the default from tools/gen_panel.py.")
    y.append("")
    y.append("input_text:")
    for n in range(1, len(BUTTONS) + 1):
        y.append(f"  cyd_btn_{n}_label: {{ name: CYD Button {n} Label, max: 20 }}")
        y.append(f"  cyd_btn_{n}_entity: {{ name: CYD Button {n} Entity, max: 100 }}")
    y.append("")
    y.append("openhasp:")
    y.append(f"  {PLATE}:")
    y.append("    objects:")
    for ref, props, event in bindings:
        y.append(f"      - obj: \"{ref}\"")
        if props:
            y.append("        properties:")
            for k, v in props.items():
                y.append(f"          \"{k}\": {q(v)}")
        if event:
            y.append("        event:")
            for ev, actions in event.items():
                y.append(f"          \"{ev}\":")
                for act in actions:
                    if "push" in act:
                        d = act["push"]
                        y.append("            - service: openhasp.push_image")
                        y.append(f"              target: {{ entity_id: openhasp.{PLATE} }}")
                        y.append("              data:")
                        y.append(f"                obj: {d['obj']}")
                        y.append(f"                image: {q(d['image'])}")
                        y.append(f"                width: {d['width']}")
                        y.append(f"                height: {d['height']}")
                        y.append(f"                fitscreen: {str(d['fitscreen']).lower()}")
                    elif "condition" in act:
                        y.append("            - condition: template")
                        y.append(f"              value_template: {q(act['condition'])}")
                    else:
                        y.append(f"            - service: {act['service']}")
                        y.append("              target:")
                        y.append(f"                entity_id: {q(act['entity_id'])}")
    (ROOT / "ha" / "packages" / "hazy_cyd.yaml").write_text("\n".join(y) + "\n")


if __name__ == "__main__":
    write_jsonl()
    write_yaml()
    per_page = {}
    for o in lines:
        per_page[o["page"]] = per_page.get(o["page"], 0) + 1
    print("objects per page:", per_page, "bindings:", len(bindings))
