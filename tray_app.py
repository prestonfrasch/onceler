# tray_app.py
from PIL import Image, ImageDraw, ImageFont
import pystray, threading, time, math
from storage import DB
from impact import CFG

SIZE=64

def make_icon(trees: float):
    base = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
    d = ImageDraw.Draw(base)
    # tree: simple triangles + trunk
    d.polygon([(32,8),(18,28),(46,28)], fill=(34,139,34,255))
    d.polygon([(32,18),(14,38),(50,38)], fill=(34,139,34,255))
    d.polygon([(32,28),(10,48),(54,48)], fill=(34,139,34,255))
    d.rectangle([(28,48),(36,60)], fill=(101,67,33,255))
    # ring progress
    frac = max(0.0, trees - math.floor(trees))
    if frac > 0:
        d.arc([6,6,SIZE-6,SIZE-6], start=-90, end=-90 + int(360*frac), width=5, fill=(120,120,120,255))
    # badge = floor(tree-days) as small dot text
    n = int(math.floor(trees))
    if n>0:
        txt = str(n)
        # Try default font; Pillow will fallback
        d.ellipse([46,46,62,62], fill=(240,240,240,255))
        d.text((49,48), txt, fill=(0,0,0,255))
    # flames when >=1 tree-day
    if trees >= 1.0:
        d.polygon([(16,20),(20,8),(24,20)], fill=(255,69,0,200))
        d.polygon([(40,16),(44,6),(48,18)], fill=(255,99,71,200))
    return base

def run_tray():
    db = DB()
    icon = pystray.Icon("AI Impact")
    icon.icon = make_icon(0.0)
    icon.title = "AI Impact"
    def updater():
        while icon.visible:
            t = db.totals()
            trees = (t["gco2"] / CFG["tree_gco2_per_day"]) if CFG["tree_gco2_per_day"] else 0.0
            icon.icon = make_icon(trees)
            icon.visible = True
            time.sleep(2)
    th = threading.Thread(target=updater, daemon=True)
    th.start()
    icon.run()

if __name__ == "__main__":
    run_tray()
