from PIL import Image, ImageDraw, ImageFont, Image
import pystray, threading, time, math
from pathlib import Path

from storage import DB          # Uses the shared DB next to storage.py
from impact import CFG          # Reads config.json

ICON_SIZE   = 64
POLL_SECONDS = 2
TREE_GCO2_PER_DAY = float(CFG.get("tree_gco2_per_day", 59.726027397260275))

# --- MSPainty palette ---
GREEN_DARK  = (20,  92,  24, 255)
GREEN       = (36,  140, 40, 255)
GREEN_LIGHT = (60,  180, 66, 255)
BROWN       = (120, 76,  42, 255)
BROWN_DARK  = (86,  54,  30, 255)
RING_BASE   = (80,  80,  80, 255)
RING_FILL   = (255, 140, 0, 255)
WHITE       = (255, 255, 255, 255)
RED         = (210, 30,  30, 255)
RED_DARK    = (140, 20,  20, 255)
OUTLINE     = (0,   0,   0, 255)

def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    """
    Robust text sizing across Pillow versions:
    - Prefer draw.textbbox (Pillow 8+; good in Pillow 10+).
    - Fall back to draw.textsize (older Pillow).
    - Fall back to font.getbbox (Pillow 10+ fonts).
    - Last resort: heuristic width.
    """
    try:
        # Preferred in modern Pillow
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        return right - left, bottom - top
    except Exception:
        pass
    try:
        # Older Pillow
        return draw.textsize(text, font=font)
    except Exception:
        pass
    try:
        # Pillow 10+ font API
        left, top, right, bottom = font.getbbox(text)
        return right - left, bottom - top
    except Exception:
        # Heuristic fallback
        return max(6, int(len(text) * 7)), 12

def _chunky_rect(d: ImageDraw.ImageDraw, box, fill, outline=OUTLINE, width=3):
    d.rectangle(box, fill=fill, outline=outline, width=width)

def _chunky_triangle(d: ImageDraw.ImageDraw, pts, fill, outline=OUTLINE):
    d.polygon(pts, fill=fill, outline=outline)

def _chunky_arc(d: ImageDraw.ImageDraw, box, start, end, fill, width=6):
    d.arc(box, start=start, end=end, fill=fill, width=width)

def _draw_mspainty_tree(d: ImageDraw.ImageDraw, w: int, h: int):
    # Blocky layered canopy (3 tiers), chunky outlines
    cx = w // 2
    tier_h = int(h * 0.12)
    base_y = int(h * 0.52)
    # bottom tier (wide)
    _chunky_triangle(
        d,
        [(cx, base_y - tier_h*0 - 8),
         (cx - int(w*0.35), base_y + tier_h),
         (cx + int(w*0.35), base_y + tier_h)],
        GREEN
    )
    # middle tier
    _chunky_triangle(
        d,
        [(cx, base_y - tier_h*2 - 4),
         (cx - int(w*0.28), base_y),
         (cx + int(w*0.28), base_y)],
        GREEN_LIGHT
    )
    # top tier
    _chunky_triangle(
        d,
        [(cx, base_y - tier_h*4 - 0),
         (cx - int(w*0.20), base_y - tier_h*2),
         (cx + int(w*0.20), base_y - tier_h*2)],
        GREEN
    )
    # extra chunky "leaf" squares for MS Paint energy
    leaf_sz = int(w*0.06)
    _chunky_rect(d, [cx - int(w*0.28), base_y - tier_h,
                     cx - int(w*0.28) + leaf_sz, base_y - tier_h + leaf_sz],
                 GREEN_DARK, OUTLINE, 2)
    _chunky_rect(d, [cx + int(w*0.18), base_y - tier_h*2,
                     cx + int(w*0.18) + leaf_sz, base_y - tier_h*2 + leaf_sz],
                 GREEN_DARK, OUTLINE, 2)

    # Trunk: chunky block with shading
    trunk_w = int(w * 0.18)
    trunk_h = int(h * 0.22)
    tx0 = cx - trunk_w // 2
    ty0 = int(h * 0.60)
    _chunky_rect(d, [tx0, ty0, tx0 + trunk_w, ty0 + trunk_h], BROWN, OUTLINE, 3)
    _chunky_rect(d, [tx0 + int(trunk_w*0.55), ty0, tx0 + trunk_w, ty0 + trunk_h], BROWN_DARK, OUTLINE, 1)

def _draw_badge(img: Image.Image, n: int):
    if n <= 0:
        return
    d = ImageDraw.Draw(img)
    w, h = img.size
    r = int(min(w, h) * 0.22)
    cx, cy = int(w * 0.82), int(h * 0.20)
    bbox = [cx - r, cy - r, cx + r, cy + r]
    d.ellipse(bbox, fill=RED, outline=RED_DARK, width=3)
    try:
        font = ImageFont.truetype("segoeui.ttf", size=int(r * 1.1))
    except Exception:
        font = ImageFont.load_default()
    label = "9+" if n >= 10 else str(n)
    tw, th = _measure_text(d, label, font)
    d.text((cx - tw/2, cy - th/2 - 1), label, fill=WHITE, font=font)

def _make_icon(trees: float) -> Image.Image:
    w = h = ICON_SIZE
    img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)

    # Chunky ring (track + progress)
    pad = int(w * 0.05)
    box = [pad, pad, w - pad, h - pad]
    _chunky_arc(d, box, 0, 360, RING_BASE, width=6)
    frac = max(0.0, trees - math.floor(trees))
    if frac > 0:
        _chunky_arc(d, box, -90, -90 + int(360 * frac), RING_FILL, width=8)

    # Tree
    _draw_mspainty_tree(d, w, h)

    # Flames for >= 1.0 (chunky circles/triangle combo)
    if trees >= 1.0:
        cx, cy = int(w * 0.70), int(h * 0.30)
        r = int(min(w, h) * 0.20)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 140, 0, 230), outline=OUTLINE, width=3)
        d.polygon([(cx, cy - r), (cx - r//2, cy + r//2), (cx + r//2, cy + r//2)],
                  fill=(255, 200, 40, 230), outline=OUTLINE)

    # Badge with whole trees
    whole = int(math.floor(trees))
    _draw_badge(img, whole)
    return img

class TrayApp:
    def __init__(self):
        self.db = DB()          # shared DB next to storage.py
        self.icon = None
        self._stop = threading.Event()
        self.baseline_g = 0.0   # gCO2 baseline

    def _totals(self):
        t = self.db.totals()
        return float(t.get("gco2", 0.0)), float(t.get("liters", 0.0))

    def _trees(self, g: float) -> float:
        used = max(0.0, g - self.baseline_g)
        return (used / TREE_GCO2_PER_DAY) if TREE_GCO2_PER_DAY else 0.0

    def _update_once(self):
        g, L = self._totals()
        trees = self._trees(g)
        if self.icon:
            self.icon.icon = _make_icon(trees)
            # Tooltip: CO2 + Water + Tree-days
            self.icon.title = f"AI Impact — CO₂: {g:.1f} g | Water: {L:.2f} L | Tree-days: {trees:.2f}"

    def _loop(self):
        while not self._stop.is_set():
            try:
                self._update_once()
            except Exception:
                pass
            time.sleep(POLL_SECONDS)

    # Menu actions
    def _reset(self, icon=None, item=None):
        g, _ = self._totals()
        self.baseline_g = g
        self._update_once()

    def _open_folder(self, icon=None, item=None):
        import os, sys
        folder = str(Path(self.db.path).resolve().parent)
        if sys.platform.startswith("win"):
            os.startfile(folder)
        elif sys.platform.startswith("darwin"):
            os.system(f'open "{folder}"')
        else:
            os.system(f'xdg-open "{folder}"')

    def _quit(self, icon=None, item=None):
        self._stop.set()
        time.sleep(0.15)
        if self.icon:
            self.icon.stop()

    def run(self):
        # Quit is in the menu only (NOT default), so double-click will not close the app
        menu = pystray.Menu(
            pystray.MenuItem("Reset Counter (set baseline)", self._reset),
            pystray.MenuItem("Open DB Folder", self._open_folder),
            pystray.MenuItem("Quit", self._quit),
        )
        # Start with current totals for initial tooltip (optional)
        g0, L0 = self._totals()
        t0 = self._trees(g0)
        initial_title = f"AI Impact — CO₂: {g0:.1f} g | Water: {L0:.2f} L | Tree-days: {t0:.2f}"

        self.icon = pystray.Icon("AI Impact", _make_icon(t0), initial_title, menu)
        threading.Thread(target=self._loop, daemon=True).start()
        self.icon.run()

if __name__ == "__main__":
    TrayApp().run()
