"""pixel-morning: turn a 10 EUR iPixel LED panel into a bedside morning board.

    python morning.py preview          build today's board, save GIF to preview/
    python morning.py push             build it and send it to the panel
    python morning.py text "GM"        quick message
    python morning.py night            dim clock for the night
    python morning.py schedule         store on/off times on the panel itself
    python morning.py scan             find the panel's Bluetooth address
"""
import argparse
import asyncio
import datetime as dt
import json
import sys
import tomllib
import urllib.request
from pathlib import Path

import pixels as px

ROOT = Path(__file__).parent
DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def load_config() -> dict:
    path = ROOT / "config.toml"
    if not path.exists():
        path = ROOT / "config.example.toml"
    with open(path, "rb") as f:
        return tomllib.load(f)


# ---------- data ----------

def weather(lat: float, lon: float) -> dict | None:
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code"
           "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
           "&timezone=auto&forecast_days=1")
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            d = json.load(r)
    except Exception as e:  # no internet -> board still works without weather
        print(f"weather skipped: {e}", file=sys.stderr)
        return None
    code = d["current"]["weather_code"]
    rain_pct = d["daily"]["precipitation_probability_max"][0] or 0
    if code in (71, 73, 75, 77, 85, 86):
        icon, word = "snow", "SNOW"
    elif code >= 51 or rain_pct >= 60:
        icon, word = "rain", "UMBRELLA" if rain_pct >= 60 else "RAIN"
    elif code >= 2:
        icon, word = "cloud", "CLOUDY"
    else:
        icon, word = "sun", "SUNNY"
    return {
        "icon": icon, "word": word,
        "now": round(d["current"]["temperature_2m"]),
        "hi": round(d["daily"]["temperature_2m_max"][0]),
        "lo": round(d["daily"]["temperature_2m_min"][0]),
    }


def breakfast(cfg: dict, today: dt.date) -> str:
    options = cfg.get("breakfast", {}).get("options", [])
    if not options:
        return ""
    return options[today.toordinal() % len(options)]  # rotates daily, no repeats in a row


# ---------- board ----------

def build_board(cfg: dict, today: dt.date | None = None):
    today = today or dt.date.today()
    weekend = today.weekday() >= 5
    hold = cfg.get("board", {}).get("seconds_per_card", 3) * 1000
    frames, durations = [], []

    def add(img, ms=hold):
        frames.append(img)
        durations.append(ms)

    name = cfg.get("board", {}).get("name", "")
    add(px.card_text(["GOOD", "MORNING", name.upper()] if name else ["GOOD", "MORNING"]))
    add(px.card_text([DAYS[today.weekday()], f"{today.day} {MONTHS[today.month - 1]}"]))

    w = weather(cfg["location"]["lat"], cfg["location"]["lon"])
    if w:
        add(px.card_weather(w["icon"], w["now"], w["hi"], w["lo"], w["word"]))

    note = cfg.get("today", {}).get(DAYS[today.weekday()].lower())
    if note:
        add(px.card_icon_label("bag", note, accent=(255, 110, 30)), hold + 1000)

    steps = cfg["routine"]["weekend" if weekend else "weekday"]
    for i, step in enumerate(steps, 1):
        label = step["label"]
        if label.upper() == "{BREAKFAST}":
            label = breakfast(cfg, today) or "BREAKFAST"
        add(px.card_icon_label(step["icon"], label, step=f"{i}/{len(steps)}"))

    add(px.card_icon_label("heart", cfg.get("board", {}).get("sign_off", "GO GET IT")), hold)
    return frames, durations


# ---------- panel ----------

def address(cfg: dict) -> str:
    addr = cfg.get("panel", {}).get("address", "")
    if addr:
        return addr
    from bleak import BleakScanner
    found = asyncio.run(BleakScanner.discover(timeout=8))
    for d in found:
        if d.name and d.name.startswith("LED_BLE_"):
            print(f"found {d.name} at {d.address} (put it in config.toml to skip the scan)")
            return d.address
    sys.exit("No LED_BLE_* panel found. Is it powered and not connected to the phone app?")


def panel(cfg: dict):
    from pypixelcolor import Client
    c = Client(address(cfg))
    c.connect()
    return c


def cmd_preview(cfg, args):
    frames, durations = build_board(cfg)
    out = ROOT / "preview"
    out.mkdir(exist_ok=True)
    px.save_gif(frames, durations, out / "board.gif")
    px.save_preview(frames, durations, out / "board_big.gif")
    print(f"{len(frames)} cards -> preview/board.gif, preview/board_big.gif")


def cmd_push(cfg, args):
    frames, durations = build_board(cfg)
    out = ROOT / "preview"
    out.mkdir(exist_ok=True)
    gif = out / "board.gif"
    px.save_gif(frames, durations, gif)
    c = panel(cfg)
    try:
        c.set_power(True)
        c.set_brightness(cfg.get("panel", {}).get("day_brightness", 60))
        c.send_image(str(gif))
    finally:
        c.disconnect()
    print(f"pushed {len(frames)} cards")


def cmd_text(cfg, args):
    c = panel(cfg)
    try:
        c.send_text(args.message, color=args.color, animation=1)
    finally:
        c.disconnect()


def cmd_night(cfg, args):
    c = panel(cfg)
    try:
        c.set_time()
        c.set_clock_mode(style=1, show_date=False, format_24=True)
        c.set_brightness(cfg.get("panel", {}).get("night_brightness", 5))
    finally:
        c.disconnect()
    print("night clock on")


def cmd_schedule(cfg, args):
    """Store on/off times on the panel itself, so it sleeps with no PC around."""
    s = cfg.get("panel", {})
    on_h, on_m = map(int, s.get("on_at", "06:55").split(":"))
    off_h, off_m = map(int, s.get("off_at", "00:30").split(":"))
    c = panel(cfg)
    try:
        c.set_time()
        c.set_schedule(on_h, on_m, True, slot=0)
        c.set_schedule(off_h, off_m, False, slot=1)
    finally:
        c.disconnect()
    print(f"panel turns itself on at {on_h:02}:{on_m:02} and off at {off_h:02}:{off_m:02}")


def cmd_scan(cfg, args):
    cfg = dict(cfg, panel={})
    print(address(cfg))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preview")
    sub.add_parser("push")
    t = sub.add_parser("text")
    t.add_argument("message")
    t.add_argument("--color", default="00e68c")
    sub.add_parser("night")
    sub.add_parser("schedule")
    sub.add_parser("scan")
    args = ap.parse_args()
    cfg = load_config()
    {"preview": cmd_preview, "push": cmd_push, "text": cmd_text, "night": cmd_night,
     "schedule": cmd_schedule, "scan": cmd_scan}[args.cmd](cfg, args)


if __name__ == "__main__":
    main()
