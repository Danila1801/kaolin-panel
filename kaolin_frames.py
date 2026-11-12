"""Cut Kaolin's animations out of the desktop-pet sprite sheet and shrink them to 32x32 GIFs.

    python kaolin_frames.py            -> build/*.gif (panel) + build/*_big.gif (LED-look preview)

The sheet stays where the pet lives (~/projects/kaolin-pet); nothing is copied into the repo.
"""
import json
import os
from pathlib import Path

from PIL import Image, ImageEnhance

import pixels

def _pet_dir() -> Path:
    if os.environ.get("KAOLIN_PET_DIR"):
        return Path(os.environ["KAOLIN_PET_DIR"])
    for p in (Path.home() / "projects" / "kaolin-pet", Path(os.environ.get("LOCALAPPDATA", "")) / "KaolinPet"):
        if (p / "kaolin_sheet.png").exists():
            return p
    raise SystemExit("Kaolin sprite sheet not found; set KAOLIN_PET_DIR")


PET_DIR = _pet_dir()
OUT = Path(__file__).parent / "build"
SIZE = 32

# state -> list of (animation, repeats). One GIF per state.
STATES = {
    "done": [("staff_spin_start", 1), ("staff_spin", 1), ("staff_spin_end", 1)],
    "ready": [("idle", 1)],
    "working": [("sleep", 1)],
    "waiting": [("grip_cast", 1)],
}


def load_sheet():
    sheet = Image.open(PET_DIR / "kaolin_sheet.png").convert("RGBA")
    meta = json.loads((PET_DIR / "kaolin_sheet.json").read_text())
    return sheet, meta


def frames_of(sheet, meta, name):
    fw, fh = meta["frameWidth"], meta["frameHeight"]
    a = meta["animations"][name]
    return [sheet.crop((i * fw, a["row"] * fh, (i + 1) * fw, (a["row"] + 1) * fh))
            for i in range(a["frames"])], a["fps"]


def union_bbox(frames):
    boxes = [f.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox() for f in frames]
    boxes = [b for b in boxes if b]
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def shrink(frame, box):
    """Crop to the shared box, fit into 32x32 bottom-centred, on black."""
    f = frame.crop(box)
    scale = min(SIZE / f.width, SIZE / f.height)
    w, h = max(1, round(f.width * scale)), max(1, round(f.height * scale))
    f = f.resize((w, h), Image.LANCZOS)
    # punchier colours: LEDs wash out mid-tones
    rgb = ImageEnhance.Color(f.convert("RGB")).enhance(1.15)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.2)
    alpha = f.getchannel("A").point(lambda v: 255 if v > 90 else 0)
    canvas = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    canvas.paste(rgb, ((SIZE - w) // 2, SIZE - h), alpha)
    return boost_green(canvas)


def boost_green(img):
    """Push the jade glow to full LED green so the staff tips read from across the room."""
    px = img.load()
    for y in range(SIZE):
        for x in range(SIZE):
            r, g, b = px[x, y]
            if g > 200 and g > r * 1.7 and g > b * 1.5:
                px[x, y] = (min(255, r // 2), 255, min(255, b // 2 + 40))
    return img


def build():
    sheet, meta = load_sheet()
    used = {a for seq in STATES.values() for a, _ in seq}
    # one crop box for every animation, so Kaolin doesn't jump in size between states
    all_frames = [f for a in used for f in frames_of(sheet, meta, a)[0]]
    box = union_bbox(all_frames)
    OUT.mkdir(exist_ok=True)
    for state, seq in STATES.items():
        frames, durations = [], []
        for anim, reps in seq:
            fr, fps = frames_of(sheet, meta, anim)
            small = [shrink(f, box) for f in fr]
            for _ in range(reps):
                frames += small
                durations += [round(1000 / fps)] * len(small)
        pixels.save_gif(frames, durations, OUT / f"{state}.gif")
        pixels.save_preview(frames, durations, OUT / f"{state}_big.gif")
        print(f"{state}: {len(frames)} frames, box {box}")


if __name__ == "__main__":
    build()
