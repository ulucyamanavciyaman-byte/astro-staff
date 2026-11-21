#!/usr/bin/env python3
"""3D models + textures for Astro Mutfak (used by turk_kitchen.py).
 - Ocak: overrides the vanilla smoker block model (smoker / smoker_on) with a real stove:
   glass cooktop, gas burner, cast iron pan supports, knobs, oven door with a window that glows when lit.
 - Vessels (tava, tencere, tepsi, tahta, cezve, kase, caydanlik) + lid + whisk as 3D item models.
 - Appliances (k_*) as 3D item models shown with item_display entities in the kitchen.
All models: front = north (-Z), handles point to +X.
"""
import json, math
import turk_food as tf

def rgb(h): return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
def clamp(v): return max(0, min(255, int(v)))
def h32(*a):
    x = 2166136261
    for v in a:
        x ^= (int(v) & 0xffffffff); x = (x * 16777619) & 0xffffffff
    x ^= x >> 13; x = (x * 1274126177) & 0xffffffff
    return (x & 0xffff) / 65535.0

class T:
    def __init__(s, base, seed=1):
        s.seed = seed
        c = rgb(base) if isinstance(base, str) else base
        s.p = [[(c[0], c[1], c[2], 255) for _ in range(16)] for _ in range(16)]
    def set(s, x, y, c, a=255):
        if 0 <= x < 16 and 0 <= y < 16:
            c = rgb(c) if isinstance(c, str) else c
            s.p[y][x] = (clamp(c[0]), clamp(c[1]), clamp(c[2]), a)
    def get(s, x, y): return s.p[y][x]
    def mul(s, x, y, f):
        r, g, b, a = s.p[y][x]; s.p[y][x] = (clamp(r * f), clamp(g * f), clamp(b * f), a)
    def rect(s, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): s.set(x, y, c)
    def frame(s, x0, y0, x1, y1, c):
        for x in range(x0, x1 + 1): s.set(x, y0, c); s.set(x, y1, c)
        for y in range(y0, y1 + 1): s.set(x0, y, c); s.set(x1, y, c)
    def noise(s, amt, salt=0):
        for y in range(16):
            for x in range(16): s.mul(x, y, 1 + (h32(s.seed, salt, x, y) - .5) * 2 * amt)
    def hlines(s, amt, salt=3):  # brushed metal
        for y in range(16):
            f = 1 + (h32(s.seed, salt, y) - .5) * 2 * amt
            for x in range(16): s.mul(x, y, f * (1 + (h32(s.seed, salt + 9, x, y) - .5) * amt * .6))
    def vgrad(s, top, bot):
        for y in range(16):
            f = top + (bot - top) * y / 15
            for x in range(16): s.mul(x, y, f)
    def disc(s, cx, cy, r, c, r0=0):
        for y in range(16):
            for x in range(16):
                d = math.hypot(x + .5 - cx, y + .5 - cy)
                if r0 <= d <= r: s.set(x, y, c)
    def png(s): return tf.png(None, s.p)

# ----------------------------------------------------------------------------- textures
def textures():
    t = {}
    # metals
    a = T("c9ccd1", 1); a.hlines(.06); t["steel"] = a
    a = T("8a8e96", 2); a.hlines(.07); t["steel_dark"] = a
    a = T("e6e9ee", 3); a.vgrad(1.08, .82); a.hlines(.03)
    for x in range(16): a.mul(x, 4, 1.12); a.mul(x, 11, .85)
    t["chrome"] = a
    a = T("1d1d20", 4); a.noise(.05); t["black"] = a
    a = T("2b2a2a", 5); a.noise(.12); t["iron"] = a
    a = T("2e2f33", 6); a.noise(.10)
    for i in range(14): a.mul(int(h32(6, i) * 16), int(h32(7, i) * 16), 1.5)
    t["nonstick"] = a
    a = T("b8673a", 7); a.noise(.10)
    for i in range(20): a.mul(int(h32(8, i) * 16), int(h32(9, i) * 16), 1.25)
    for x in range(16): a.mul(x, 2, 1.15); a.mul(x, 13, .8)
    t["copper"] = a
    a = T("c9a24a", 8); a.vgrad(1.1, .85); a.noise(.05); t["brass"] = a
    # woods
    a = T("c8955a", 9)
    for y in range(16):
        for x in range(16):
            w = math.sin((y + math.sin(x * .7 + 1.3) * 1.4) * 1.9)
            a.mul(x, y, 1 + w * .06 + (h32(9, x, y) - .5) * .05)
    t["wood"] = a
    a = T("5e4030", 10)
    for y in range(16):
        for x in range(16):
            w = math.sin((x + math.sin(y * .6) * 1.2) * 2.1)
            a.mul(x, y, 1 + w * .07 + (h32(10, x, y) - .5) * .05)
    t["wood_dark"] = a
    # cabinet door: light oak shaker panel
    a = T("d9b98a", 11)
    for y in range(16):
        for x in range(16): a.mul(x, y, 1 + math.sin((y + math.sin(x * .5) * 1.2) * 1.7) * .04)
    a.frame(0, 0, 15, 15, "a8865a"); a.frame(2, 2, 13, 13, "b8966a"); a.frame(3, 3, 12, 12, "e6c899")
    t["cab_door"] = a
    a = T("d9b98a", 12)
    for y in range(16):
        for x in range(16): a.mul(x, y, 1 + math.sin((x + math.sin(y * .5)) * 1.3) * .04)
    for yy in (0, 5, 10, 15):
        for x in range(16): a.set(x, yy, "8a6a40")
    for x in range(16): a.set(x, 4, "a8865a"); a.set(x, 9, "a8865a"); a.set(x, 14, "a8865a")
    for yy in (2, 7, 12):
        for x in range(6, 10): a.set(x, yy, "dfe3e8")
    t["cab_drawer"] = a
    # marble
    a = T("eeece8", 13); a.noise(.03)
    for k in range(3):
        x0, y0 = h32(13, k) * 16, h32(14, k) * 16
        for i in range(26):
            x = int(x0 + i * .7) % 16; y = int(y0 + math.sin(i * .5 + k) * 3 + i * .35) % 16
            a.set(x, y, "b8b6b4" if i % 3 else "9a9896")
    t["marble"] = a
    a = T("f3f3f0", 14); a.vgrad(1.02, .95); a.noise(.02); t["white"] = a
    a = T("17181c", 15)
    for y in range(16):
        for x in range(16):
            if 3 <= (x - y + 16) % 16 <= 4: a.set(x, y, "34363c")
    t["glass_dark"] = a
    # cini (iznik blue on white)
    a = T("f4f2ec", 16); a.noise(.02)
    for y in range(16):
        for x in range(16):
            u, v = (x % 8) - 3.5, (y % 8) - 3.5
            d = math.hypot(u, v)
            if 2.2 < d < 3.2: a.set(x, y, "1f4f9a")
            elif d < 1.1: a.set(x, y, "c8302a")
            elif abs(u) < .6 or abs(v) < .6:
                if d < 2.2: a.set(x, y, "3a7ac8")
    t["cini"] = a
    a = T("3a2416", 17); a.noise(.08)
    for i in range(30): a.set(int(h32(17, i) * 16), int(h32(18, i) * 16), "8a5a34")
    t["kahve_top"] = a  # coffee foam inside cezve
    # appliance fronts
    a = T("c9ccd1", 18); a.hlines(.05)  # microwave
    a.rect(1, 2, 10, 13, "141519"); a.frame(1, 2, 10, 13, "5a5e66")
    for y in range(3, 13):
        for x in range(2, 10):
            if (x - y + 20) % 7 == 0: a.set(x, y, "2a2c33")
    a.rect(11, 2, 14, 13, "2a2c31"); a.rect(12, 3, 13, 4, "6ad06a")
    for yy in (6, 8, 10):
        a.set(12, yy, "9aa0aa"); a.set(13, yy, "9aa0aa")
    a.disc(12.5 + .5, 12, 1.2, "8a9098")
    t["mikro_front"] = a
    a = T("c9ccd1", 19); a.hlines(.05)  # dishwasher
    a.rect(0, 0, 15, 2, "2a2c31"); a.set(3, 1, "6ad06a"); a.set(5, 1, "d04a3a"); a.set(11, 1, "9aa0aa"); a.set(12, 1, "9aa0aa")
    for x in range(16): a.mul(x, 15, .7)
    t["bulasik_front"] = a
    a = T("c9ccd1", 20); a.hlines(.05)  # hood front
    a.rect(0, 12, 15, 15, "8a8e96")
    for x in range(2, 14, 3): a.set(x, 14, "fff4c0")
    t["aspirator_front"] = a
    a = T("1d1d20", 21); a.noise(.04)  # coffee machine
    a.rect(4, 6, 11, 14, "0a0a0c"); a.rect(6, 10, 9, 14, "b8673a"); a.rect(6, 10, 9, 10, "d8875a")
    a.rect(4, 2, 11, 3, "3a3c42"); a.set(5, 2, "6ad06a"); a.set(10, 2, "d04a3a")
    t["kahve_front"] = a
    a = T("c9ccd1", 22); a.hlines(.05)  # toaster
    a.disc(8, 9, 2.2, "2a2c31"); a.set(8, 8, "e8e8e8"); a.rect(0, 15, 15, 15, "5a5e66")
    t["tost_front"] = a
    a = T("dde0e5", 23); a.hlines(.04)  # fridge door (inox)
    for x in range(16): a.mul(x, 0, .8); a.mul(x, 15, .8)
    t["fridge_door"] = a
    # spice jars + fruit
    for nm, c in (("jar_red", "c4301c"), ("jar_black", "3a3a3a"), ("jar_brown", "a8782a"), ("jar_green", "6a8a3a"), ("jar_white", "f4f4f0")):
        a = T("dfe9ee", 24 + len(nm))
        a.rect(1, 4, 14, 15, c); a.noise(.07)
        for y in range(16): a.set(2, y, "ffffff") if y > 4 else None
        t[nm] = a
    a = T("b8bcc4", 30); a.hlines(.05); t["lid"] = a
    for nm, c in (("fruit_red", "c8221c"), ("fruit_orange", "f0901c"), ("fruit_green", "8ac03a"), ("fruit_yellow", "f2d83a")):
        a = T(c, 31 + len(nm)); a.vgrad(1.15, .8); a.noise(.05); a.set(4, 4, (255, 255, 255)); t[nm] = a
    a = T("2a2224", 40); a.noise(.06); t["leather"] = a
    return t

def block_textures():
    t = {}
    # cooktop (seen from above)
    for on in (False, True):
        a = T("1a1b1f", 50); a.noise(.04)
        for y in range(16):
            for x in range(16):
                if 3 <= (x + y) % 19 <= 4: a.mul(x, y, 1.4)
        a.frame(0, 0, 15, 15, "8a8e96")
        a.disc(8, 8, 4.6, "4a4c52", 3.4); a.disc(8, 8, 3.4, "2a2b2f"); a.disc(8, 8, 1.7, "101012")
        if on:
            a.disc(8, 8, 4.3, "3a78ff", 3.2); a.disc(8, 8, 3.9, "9ad0ff", 3.5)
        t["ocak_top" + ("_on" if on else "")] = a
    for on in (False, True):
        a = T("c9ccd1", 51); a.hlines(.05)
        a.rect(0, 0, 15, 3, "3a3c42")                     # control panel
        for x in (2, 5, 10, 13): a.set(x, 1, "6ad06a" if on else "5a5e66")
        a.frame(0, 4, 15, 15, "8a8e96")                   # oven door frame
        a.rect(2, 7, 13, 13, "141519")                    # window
        if on:
            for y in range(7, 14):
                for x in range(2, 14):
                    g = 1 - abs(y - 10) / 5
                    a.set(x, y, (255, clamp(110 + 90 * g), clamp(30 + 40 * g)))
            for x in range(3, 13): a.set(x, 11, "5a2a10")    # the tray inside
        else:
            for y in range(7, 14):
                for x in range(2, 14):
                    if (x - y + 20) % 6 == 0: a.set(x, y, "2c2e35")
        a.frame(2, 7, 13, 13, "5a5e66")
        t["ocak_front" + ("_on" if on else "")] = a
    a = T("c9ccd1", 52); a.hlines(.05); a.rect(0, 0, 15, 0, "8a8e96"); t["ocak_side"] = a
    a = T("2a2b2f", 53); a.noise(.05); t["ocak_bottom"] = a
    a = T("2b2a2a", 54); a.noise(.12); t["ocak_iron"] = a
    a = T("e6e9ee", 55); a.vgrad(1.08, .82); t["ocak_chrome"] = a
    a = T("1d1d20", 56); a.noise(.04); a.rect(7, 0, 8, 6, "e8e8e8"); t["ocak_knob"] = a
    a = T("1d1d20", 57); a.noise(.04); a.rect(7, 0, 8, 6, "ff5a3a"); t["ocak_knob_on"] = a
    return t

# ----------------------------------------------------------------------------- model helpers
FN = {"n": "north", "s": "south", "e": "east", "w": "west", "u": "up", "d": "down"}

def el(f, t, tex, rot=None, faces="nsewud", over=None, cull=None):
    """box element; tex = default texture var; over = {face: tex}; uvs are always explicit and clamped (no atlas bleed)"""
    over = over or {}
    dx, dy, dz = abs(t[0] - f[0]), abs(t[1] - f[1]), abs(t[2] - f[2])
    dims = {"n": (dx, dy), "s": (dx, dy), "e": (dz, dy), "w": (dz, dy), "u": (dx, dz), "d": (dx, dz)}
    e = {"from": [round(v, 3) for v in f], "to": [round(v, 3) for v in t], "faces": {}}
    for fc in faces:
        w, h = dims[fc]
        w, h = min(16, max(.5, w)), min(16, max(.5, h))
        face = {"texture": "#" + over.get(fc, tex), "uv": [0, 0, round(w, 3), round(h, 3)]}
        if cull and fc in cull: face["cullface"] = FN[fc]
        e["faces"][FN[fc]] = face
    if rot: e["rotation"] = {"origin": rot[0], "axis": rot[1], "angle": rot[2]}
    return e

def octo(cx, cz, a, y0, y1, tex, over=None):
    """filled octagonal prism (in-radius a)"""
    return [el([cx - a, y0, cz - a], [cx + a, y1, cz + a], tex, over=over),
            el([cx - a, y0, cz - a], [cx + a, y1 - .04, cz + a], tex, rot=([cx, y0, cz], "y", 45), over=over)]

def ring(cx, cz, a, t, y0, y1, tex):
    """hollow octagon wall (inner in-radius a, thickness t)"""
    w = 2 * a * math.tan(math.radians(22.5)) + t * .9
    out = []
    for ang in (0, 45, -45):
        out.append(el([cx - w / 2, y0, cz - a - t], [cx + w / 2, y1, cz - a], tex, rot=([cx, y0, cz], "y", ang) if ang else None))
        out.append(el([cx - w / 2, y0, cz + a], [cx + w / 2, y1, cz + a + t], tex, rot=([cx, y0, cz], "y", ang) if ang else None))
    out.append(el([cx - a - t, y0, cz - w / 2], [cx - a, y1, cz + w / 2], tex))
    out.append(el([cx + a, y0, cz - w / 2], [cx + a + t, y1, cz + w / 2], tex))
    return out

ITEM_DISPLAY = {
    "gui": {"rotation": [30, 225, 0], "translation": [0, 0, 0], "scale": [0.72, 0.72, 0.72]},
    "ground": {"rotation": [0, 0, 0], "translation": [0, 3, 0], "scale": [0.5, 0.5, 0.5]},
    "fixed": {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [0.6, 0.6, 0.6]},
    "thirdperson_righthand": {"rotation": [75, 45, 0], "translation": [0, 2.5, 0], "scale": [0.45, 0.45, 0.45]},
    "thirdperson_lefthand": {"rotation": [75, 45, 0], "translation": [0, 2.5, 0], "scale": [0.45, 0.45, 0.45]},
    "firstperson_righthand": {"rotation": [0, 45, 0], "translation": [0, 2, 0], "scale": [0.45, 0.45, 0.45]},
    "firstperson_lefthand": {"rotation": [0, 225, 0], "translation": [0, 2, 0], "scale": [0.45, 0.45, 0.45]},
    "head": {"rotation": [0, 0, 0], "translation": [0, 13, 0], "scale": [0.8, 0.8, 0.8]},
}

def model(elements, texnames, ns="item/kit/"):
    tx = {n: f"astro:{ns}{n}" for n in texnames}
    tx["particle"] = tx[texnames[0]]
    return {"textures": tx, "elements": elements, "display": ITEM_DISPLAY}

def used(els):
    s = []
    for e in els:
        for f in e["faces"].values():
            n = f["texture"][1:]
            if n not in s: s.append(n)
    return s

def M(els): return model(els, used(els))

# ----------------------------------------------------------------------------- vessels
def vessels():
    m = {}
    # TAVA (frying pan)
    e = octo(8, 8, 4.6, 0, .8, "nonstick") + ring(8, 8, 4.6, .6, 0, 2.6, "nonstick")
    e += [el([12.4, 1.2, 7.2], [14.2, 2.6, 8.8], "steel"),
          el([13.6, 1.7, 7.4], [21.5, 2.6, 8.6], "black", rot=([13.6, 1.7, 8], "z", 22.5))]
    m["v_tava"] = M(e)
    # TENCERE (pot) - open; the lid is a separate model
    e = octo(8, 8, 5, 0, .6, "steel_dark") + ring(8, 8, 5, .6, 0, 7, "steel")
    e += [el([0.6, 5.2, 7], [2.5, 6.0, 9], "black"), el([13.5, 5.2, 7], [15.4, 6.0, 9], "black")]
    m["v_tencere"] = M(e)
    e = octo(8, 8, 5.5, 0, .5, "lid") + octo(8, 8, 3.6, .5, 1.1, "lid") + [el([7, 1.1, 7], [9, 2.4, 9], "black")]
    m["v_kapak"] = M(e)
    # TEPSI (oven tray)
    e = [el([1, 0, 2], [15, .4, 14], "steel_dark"),
         el([1, 0, 2], [15, 1.5, 2.5], "steel"), el([1, 0, 13.5], [15, 1.5, 14], "steel"),
         el([1, 0, 2.5], [1.5, 1.5, 13.5], "steel"), el([14.5, 0, 2.5], [15, 1.5, 13.5], "steel"),
         el([15, 1, 6], [16.4, 1.4, 10], "steel"), el([-0.4, 1, 6], [1, 1.4, 10], "steel")]
    m["v_tepsi"] = M(e)
    # TAHTA (cutting board)
    e = [el([1.5, 0, 3], [12.5, 1, 13], "wood"), el([12.5, 0, 6.4], [16, 1, 9.6], "wood"),
         el([14.2, .99, 7.4], [15.2, 1.01, 8.6], "wood_dark")]
    m["v_tahta"] = M(e)
    # CEZVE (copper coffee pot, full of foam)
    e = octo(8, 8, 2.6, 0, 4.0, "copper") + octo(8, 8, 3.1, 3.4, 4.4, "copper", over={"u": "kahve_top"})
    e += [el([4.3, 3.8, 7.4], [5.1, 4.5, 8.6], "copper"),
          el([10.6, 2.8, 7.5], [18.5, 3.5, 8.5], "brass", rot=([10.6, 2.8, 8], "z", 22.5))]
    m["v_cezve"] = M(e)
    # KASE (mixing bowl)
    e = octo(8, 8, 3, 0, 1, "steel_dark") + octo(8, 8, 4.4, 1, 2, "steel") + ring(8, 8, 4.4, .5, 1, 5.2, "steel")
    m["v_kase"] = M(e)
    # CAYDANLIK (Turkish double teapot: kettle + porcelain demlik on top)
    e = octo(8, 8, 4.3, 0, 6.2, "steel") + octo(8, 8, 3.6, 6.2, 6.8, "steel")
    e += octo(8, 8, 3, 6.8, 10.6, "cini") + octo(8, 8, 2.2, 10.6, 11.2, "cini") + [el([7.3, 11.2, 7.3], [8.7, 12.2, 8.7], "black")]
    e += [el([12.0, 2.6, 7.4], [15.6, 3.6, 8.6], "steel", rot=([12.0, 2.6, 8], "z", 45)),
          el([10.6, 8.0, 7.5], [13.4, 8.8, 8.5], "cini", rot=([10.6, 8.0, 8], "z", 22.5)),
          el([1.3, 2, 7.4], [2.1, 6, 8.6], "black"), el([2.1, 5.4, 7.4], [3.8, 6, 8.6], "black"),
          el([2.1, 2, 7.4], [3.8, 2.6, 8.6], "black")]
    m["v_caydanlik"] = M(e)
    # CIRPICI (whisk)
    e = [el([7.4, 8, 7.4], [8.6, 16, 8.6], "black")]
    for ang in (0, 45, -45, 90):
        r = ([8, 0, 8], "y", ang) if ang in (45, -45) else None
        if ang == 90:
            e += [el([7.9, 1, 5], [8.1, 8, 5.4], "chrome"), el([7.9, 1, 10.6], [8.1, 8, 11], "chrome"), el([7.9, .6, 5.4], [8.1, 1, 10.6], "chrome")]
        else:
            e += [el([5, 1, 7.9], [5.4, 8, 8.1], "chrome", rot=r), el([10.6, 1, 7.9], [11, 8, 8.1], "chrome", rot=r),
                  el([5.4, .6, 7.9], [10.6, 1, 8.1], "chrome", rot=r)]
    m["v_cirpici"] = M(e)
    return m

# ----------------------------------------------------------------------------- appliances
def counter(e):
    return e + [el([0, 15, -0.8], [16, 16, 16], "marble")]

def appliances():
    m = {}
    # fridge (2 blocks tall, inox)
    e = [el([0, 0, .6], [16, 32, 16], "steel"),
         el([.2, .2, 0], [15.8, 21.6, .6], "steel", over={"n": "fridge_door"}),
         el([.2, 21.9, 0], [15.8, 31.8, .6], "steel", over={"n": "fridge_door"}),
         el([13, 8, -0.9], [13.9, 19, 0], "chrome"), el([13, 23.5, -0.9], [13.9, 30, 0], "chrome"),
         el([3, 13, -0.1], [7, 19, 0], "glass_dark")]
    m["k_buzdolabi"] = M(e)
    # base cabinet with marble counter (over a barrel)
    e = [el([0, 1, .6], [16, 15, 16], "wood_dark"), el([0, 0, 1.6], [16, 1, 16], "black"),
         el([.3, 1.2, .1], [7.9, 14.8, .6], "wood_dark", over={"n": "cab_door"}),
         el([8.1, 1.2, .1], [15.7, 14.8, .6], "wood_dark", over={"n": "cab_door"}),
         el([5, 12.6, -0.5], [7.3, 13.2, .1], "chrome"), el([8.7, 12.6, -0.5], [11, 13.2, .1], "chrome")]
    m["k_dolap"] = M(counter(e))
    e = [el([0, 1, .6], [16, 15, 16], "wood_dark"), el([0, 0, 1.6], [16, 1, 16], "black"),
         el([.3, 1.2, .1], [15.7, 14.8, .6], "wood_dark", over={"n": "cab_drawer"})]
    m["k_cekmece"] = M(counter(e))
    e = [el([0, 1, .6], [16, 15, 16], "steel"), el([0, 0, 1.6], [16, 1, 16], "black"),
         el([.3, 1.2, .1], [15.7, 14.8, .6], "steel", over={"n": "bulasik_front"}),
         el([2, 11.4, -0.6], [14, 12.0, .1], "chrome")]
    m["k_bulasik"] = M(counter(e))
    # sink: cabinet front + marble frame around a water cauldron + gooseneck tap
    e = [el([.3, 1.2, -0.6], [7.9, 14.8, -0.1], "wood_dark", over={"n": "cab_door"}),
         el([8.1, 1.2, -0.6], [15.7, 14.8, -0.1], "wood_dark", over={"n": "cab_door"}),
         el([5, 12.6, -1.1], [7.3, 13.2, -0.6], "chrome"), el([8.7, 12.6, -1.1], [11, 13.2, -0.6], "chrome"),
         el([0, 16, -0.8], [16, 16.6, 2], "marble"), el([0, 16, 14], [16, 16.6, 16], "marble"),
         el([0, 16, 2], [2, 16.6, 14], "marble"), el([14, 16, 2], [16, 16.6, 14], "marble"),
         el([7, 16.6, 13.6], [9, 17.4, 15.4], "chrome"), el([7.5, 17.4, 14], [8.5, 24, 15], "chrome"),
         el([7.5, 23, 7], [8.5, 24, 15], "chrome"), el([7.5, 21.8, 7], [8.5, 23, 8], "chrome"),
         el([8.5, 23.4, 13.8], [12, 24, 14.6], "chrome")]
    m["k_lavabo"] = M(e)
    # microwave
    m["k_mikrodalga"] = M([el([1, 0, 3], [15, 8.5, 14], "steel", over={"n": "mikro_front"}),
                           el([1.4, -0.01, 3.4], [2.4, .3, 4.4], "black"), el([13.6, -0.01, 3.4], [14.6, .3, 4.4], "black")])
    # range hood canopy + chimney
    m["k_aspirator"] = M([el([0, 0, 4], [16, 2, 16], "steel", over={"n": "aspirator_front"}),
                          el([.5, -0.2, 4.5], [15.5, 0, 15.5], "steel_dark")])
    m["k_baca"] = M([el([4, 0, 9], [12, 16, 16], "steel")])
    # toaster
    m["k_tost"] = M([el([3.5, 0, 4.5], [12.5, 5.5, 11.5], "steel", over={"n": "tost_front", "s": "tost_front"}),
                     el([5, 5.5, 6], [11, 5.65, 7], "black"), el([5, 5.5, 9], [11, 5.65, 10], "black"),
                     el([12.5, 3.4, 7.5], [13.4, 4.2, 8.5], "black")])
    # Turkish coffee machine
    m["k_kahve"] = M([el([3, 0, 3.5], [13, 10, 13], "black", over={"n": "kahve_front"}),
                      el([3.4, 10, 3.9], [12.6, 10.4, 12.6], "steel_dark")])
    # knife block
    r = ([8, 0, 8], "x", -22.5)
    m["k_bicaklik"] = M([el([5.5, 0, 6], [10.5, 6.5, 10], "wood_dark", rot=r)] +
                        [el([x, 6.5, 7.2], [x + .8, 9.5, 8.6], "black", rot=r) for x in (6.0, 7.2, 8.4, 9.4)])
    # spice rack (5 jars)
    e = [el([1, 0, 5.5], [15, .6, 10], "wood"), el([1, 0, 9.4], [15, 6, 10], "wood")]
    for i, j in enumerate(("jar_red", "jar_black", "jar_brown", "jar_green", "jar_white")):
        x = 1.5 + i * 2.65
        e += [el([x, .6, 6], [x + 2.3, 4.4, 8.6], j), el([x + .15, 4.4, 6.15], [x + 2.15, 5.0, 8.45], "lid")]
    m["k_baharat"] = M(e)
    # fruit bowl (cini)
    e = octo(8, 8, 2, 0, .6, "cini") + octo(8, 8, 4, .4, 1.2, "cini") + ring(8, 8, 4, .5, .4, 2.6, "cini")
    for (x, y, z, c) in ((5.4, 1.2, 5.6, "fruit_red"), (8.6, 1.2, 6.0, "fruit_orange"), (6.0, 1.2, 8.8, "fruit_green"),
                         (8.8, 1.2, 9.0, "fruit_red"), (7.2, 3.4, 7.2, "fruit_yellow")):
        e.append(el([x, y, z], [x + 2.4, y + 2.4, z + 2.4], c))
    m["k_meyve"] = M(e)
    # upper cabinet (hangs on the wall behind it, wall = south)
    m["k_ust_dolap"] = M([el([0, 0, 7], [16, 11, 16], "wood_dark"),
                          el([.3, .3, 6.5], [7.9, 10.7, 7], "wood_dark", over={"n": "cab_door"}),
                          el([8.1, .3, 6.5], [15.7, 10.7, 7], "wood_dark", over={"n": "cab_door"}),
                          el([5.5, 1, 6.0], [7.3, 1.6, 6.5], "chrome"), el([8.7, 1, 6.0], [10.5, 1.6, 6.5], "chrome")])
    # bar stool
    e = octo(8, 8, 3.2, 0, .6, "chrome") + [el([7.3, .6, 7.3], [8.7, 10, 8.7], "chrome")]
    e += ring(8, 8, 2.6, .4, 4, 4.5, "chrome") + octo(8, 8, 3.2, 10, 11.6, "leather")
    m["k_tabure"] = M(e)
    # tall pantry cabinet (2 high)
    m["k_kiler"] = M([el([0, 0, .6], [16, 32, 16], "wood_dark"),
                      el([.3, .5, .1], [15.7, 15.7, .6], "wood_dark", over={"n": "cab_door"}),
                      el([.3, 16.3, .1], [15.7, 31.5, .6], "wood_dark", over={"n": "cab_door"}),
                      el([12.5, 12, -0.5], [13.2, 15, .1], "chrome"), el([12.5, 17, -0.5], [13.2, 20, .1], "chrome")])
    return m

# ----------------------------------------------------------------------------- the Ocak (smoker block model)
def ocak_model(on):
    s = "_on" if on else ""
    e = [el([0, 0, 0], [16, 16, 16], "side", over={"n": "front", "u": "top", "d": "bottom"}, cull="nsewud")]
    for f, t in (([2, 16, 2], [14, 16.6, 3]), ([2, 16, 13], [14, 16.6, 14]), ([2, 16, 3], [3, 16.6, 13]), ([13, 16, 3], [14, 16.6, 13]),
                 ([3, 16, 7.6], [6, 17, 8.4]), ([10, 16, 7.6], [13, 17, 8.4]), ([7.6, 16, 3], [8.4, 17, 6]), ([7.6, 16, 10], [8.4, 17, 13]),
                 ([6.6, 16, 6.6], [9.4, 16.4, 9.4])):
        e.append(el(f, t, "iron"))
    for x in (2.5, 5.5, 10.5, 13.5):
        e.append(el([x - 1, 12.8, -1.2], [x + 1, 14.8, 0], "knob"))
    e += [el([3, 10.4, -1.4], [13, 11.2, -0.6], "chrome"),
          el([3.2, 10.5, -0.6], [4.0, 11.1, 0], "chrome"), el([12, 10.5, -0.6], [12.8, 11.1, 0], "chrome")]
    tex = {"side": "astro:block/ocak_side", "front": f"astro:block/ocak_front{s}", "top": f"astro:block/ocak_top{s}",
           "bottom": "astro:block/ocak_bottom", "iron": "astro:block/ocak_iron", "knob": f"astro:block/ocak_knob{s}",
           "chrome": "astro:block/ocak_chrome", "particle": "astro:block/ocak_side"}
    return {"parent": "minecraft:block/block", "textures": tex, "elements": e}

# ----------------------------------------------------------------------------- install into the pack
def install(files, add_cases):
    """files: dict path->bytes of the resource pack (modified in place). add_cases: base item -> [cmd strings]"""
    for n, im in textures().items():
        files[f"assets/astro/textures/item/kit/{n}.png"] = im.png()
    for n, im in block_textures().items():
        files[f"assets/astro/textures/block/{n}.png"] = im.png()
    for k, mdl in vessels().items():
        files[f"assets/astro/models/item/kit/{k}.json"] = json.dumps(mdl).encode()
        base = "bowl" if k not in ("v_kapak", "v_cirpici") else "paper"
        add_cases.setdefault(base, []).append((k, f"astro:item/kit/{k}"))
    for k, mdl in appliances().items():
        files[f"assets/astro/models/item/kit/{k}.json"] = json.dumps(mdl).encode()
        add_cases.setdefault("paper", []).append((k, f"astro:item/kit/{k}"))
    files["assets/minecraft/models/block/smoker.json"] = json.dumps(ocak_model(False)).encode()
    files["assets/minecraft/models/block/smoker_on.json"] = json.dumps(ocak_model(True)).encode()

def check(m):
    for e in m["elements"]:
        for v in e["from"] + e["to"]:
            assert -16 <= v <= 32, (v, e)
        if "rotation" in e: assert e["rotation"]["angle"] in (-45, -22.5, 0, 22.5, 45)

if __name__ == "__main__":
    for d in (vessels(), appliances()):
        for k, mm in d.items(): check(mm)
    check(ocak_model(True))
    print("models ok", len(vessels()), len(appliances()))
