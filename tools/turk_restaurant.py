#!/usr/bin/env python3
"""Builds the Astro "Türk Mutfağı" restaurant as datapack functions inside the mod:
  data/astro_staff/function/turk/rest_build_<dir>.mcfunction  (dir = north/south/east/west, entrance faces the player)
  data/astro_staff/function/turk/rest_clear_<dir>.mcfunction
Local frame: x = right (-11..11), z = forward / away from the player (-6..18), y = 0 is the floor.
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import turk_food as tf

ROOT = tf.ROOT
B = {}          # (x,y,z) -> block state (may contain {F:dir} / {AX} placeholders)
ENT = []        # (x,y,z, kind, data)

def put(x, y, z, s): B[(x, y, z)] = s
def fill(x0, y0, z0, x1, y1, z1, s):
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1): B[(x, y, z)] = s

QZ = "minecraft:quartz_block"; RT = "minecraft:red_terracotta"; SQ = "minecraft:smooth_quartz"
CU = "minecraft:waxed_oxidized_cut_copper"; GOLD = "minecraft:gold_block"
W0, W1, D0, D1, H = -10, 10, 0, 16, 7   # walls

def build():
    # ---------------- floor + terrace
    for x in range(-11, 12):
        for z in range(-6, 18):
            put(x, 0, z, "minecraft:polished_andesite" if (x + z) % 2 else "minecraft:andesite")
    for x in range(W0 + 1, W1):
        for z in range(D0 + 1, D1):
            put(x, 0, z, "minecraft:white_glazed_terracotta" if (x + z) % 2 == 0 else "minecraft:red_terracotta")
    # carpet runner (kilim) down the aisle
    for z in range(1, 11):
        for x in (-1, 0, 1):
            put(x, 1, z, "minecraft:red_carpet" if x == 0 else "minecraft:orange_carpet")
    # ---------------- walls (Ottoman two-tone)
    for y in range(1, H + 1):
        s = RT if y in (1, 6) else (QZ if y != 7 else "minecraft:cut_sandstone")
        for x in range(W0, W1 + 1):
            put(x, y, D0, s); put(x, y, D1, s)
        for z in range(D0, D1 + 1):
            put(W0, y, z, s); put(W1, y, z, s)
    # pillars
    for x in (W0, -5, 5, W1):
        for z in (D0, D1):
            fill(x, 1, z, x, H, z, "minecraft:chiseled_quartz_block")
    for z in (D0, 8, D1):
        for x in (W0, W1): fill(x, 1, z, x, H, z, "minecraft:chiseled_quartz_block")
    # front door: open arch 3 wide
    fill(-1, 1, D0, 1, 4, D0, "minecraft:air"); put(0, 5, D0, "minecraft:air")
    put(-1, 5, D0, "minecraft:quartz_stairs[facing={F:left},half=top]"); put(1, 5, D0, "minecraft:quartz_stairs[facing={F:right},half=top]")
    # windows (arched)
    for cx in (-7, 7):
        fill(cx - 1, 2, D0, cx + 1, 4, D0, "minecraft:light_blue_stained_glass_pane"); put(cx, 5, D0, "minecraft:light_blue_stained_glass_pane")
    for cz in (4, 12):
        for x in (W0, W1):
            fill(x, 2, cz - 1, x, 4, cz + 1, "minecraft:light_blue_stained_glass_pane"); put(x, 5, cz, "minecraft:light_blue_stained_glass_pane")
    # ---------------- roof slab + parapet
    fill(W0, H + 1, D0, W1, H + 1, D1, SQ)
    for x in range(W0, W1 + 1):
        for z in (D0, D1):
            put(x, H + 2, z, "minecraft:quartz_slab" if x % 2 else QZ)
    for z in range(D0, D1 + 1):
        for x in (W0, W1):
            put(x, H + 2, z, "minecraft:quartz_slab" if z % 2 else QZ)
    # ---------------- main dome on a drum
    cx, cz, base = 0, 8, H + 2
    for x in range(-5, 6):
        for z in range(cz - 5, cz + 6):
            d = math.hypot(x, z - cz)
            if 4.2 <= d <= 5.2:
                put(x, base, cz + (z - cz), QZ)
                put(x, base + 1, z, "minecraft:light_blue_stained_glass" if (x + z) % 3 == 0 else QZ)
    r = 5.6
    for x in range(-6, 7):
        for z in range(cz - 6, cz + 7):
            for y in range(0, 7):
                d = math.sqrt(x * x + (z - cz) ** 2 + (y * 1.0) ** 2)
                if d <= r: put(x, base + 2 + y, z, CU)
    top = base + 2 + 6
    put(0, top, cz, GOLD); put(0, top + 1, cz, "minecraft:end_rod[facing=up]"); put(0, top + 2, cz, "minecraft:lightning_rod")
    # four small corner domes
    for (ox, oz) in ((-7, 3), (7, 3), (-7, 13), (7, 13)):
        fill(ox - 1, base, oz - 1, ox + 1, base, oz + 1, QZ)
        for x in range(-2, 3):
            for z in range(-2, 3):
                for y in range(0, 3):
                    d = math.sqrt(x * x + z * z + (y * 1.2) ** 2)
                    if d <= 2.3: put(ox + x, base + 1 + y, oz + z, CU)
        put(ox, base + 4, oz, GOLD)
    # ---------------- striped awning (bayrak colours) over the front
    for x in range(-9, 10):
        c = "minecraft:red_wool" if x % 2 == 0 else "minecraft:white_wool"
        put(x, 6, -1, c); put(x, 5, -2, c)
    # terrace lanterns + planters
    for x in (-3, 3):
        fill(x, 1, -5, x, 2, -5, "minecraft:dark_oak_fence"); put(x, 3, -5, "minecraft:lantern")
    for x in (-10, -8, 8, 10):
        put(x, 1, -6, "minecraft:potted_azalea_bush" if x % 4 else "minecraft:potted_red_tulip")
    # outdoor tables with umbrellas
    for ox in (-7, 7):
        put(ox, 1, -4, "minecraft:dark_oak_fence"); put(ox, 2, -4, "minecraft:red_carpet")
        put(ox - 1, 1, -4, "minecraft:spruce_stairs[facing={F:left}]"); put(ox + 1, 1, -4, "minecraft:spruce_stairs[facing={F:right}]")
        fill(ox, 3, -4, ox, 3, -4, "minecraft:dark_oak_fence")
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                put(ox + dx, 4, -4 + dz, "minecraft:red_wool" if (dx + dz) % 2 == 0 else "minecraft:white_wool")
    # ---------------- dining hall: 6 tables with chairs
    for tx in (-6, 6):
        for tz in (3, 7, 10):
            put(tx, 1, tz, "minecraft:dark_oak_fence"); put(tx, 2, tz, "minecraft:white_carpet")
            put(tx - 1, 1, tz, "minecraft:dark_oak_stairs[facing={F:left}]"); put(tx + 1, 1, tz, "minecraft:dark_oak_stairs[facing={F:right}]")
            ENT.append((tx, 2.12, tz, "table", None))
    # hanging lamps
    for (x, z) in ((-6, 3), (-6, 7), (-6, 10), (6, 3), (6, 7), (6, 10), (0, 3), (0, 7), (0, 11), (-3, 14), (3, 14)):
        put(x, H, z, "minecraft:iron_chain"); put(x, H - 1, z, "minecraft:lantern[hanging=true]")
    # ---------------- kitchen / counter
    for x in range(-9, 10):
        put(x, 1, 12, "minecraft:dark_oak_planks"); put(x, 2, 12, "minecraft:smooth_quartz_slab")
    put(9, 1, 12, "minecraft:air"); put(9, 2, 12, "minecraft:air")  # staff gap
    for x in range(-9, 10, 2):
        ENT.append((x, 2.62, 12, "counter", None))
    # back wall equipment
    back = ["minecraft:smoker[facing={F:front},lit=true]", "minecraft:furnace[facing={F:front},lit=true]",
            "minecraft:campfire[lit=true]", "minecraft:barrel[facing=up]", "minecraft:cauldron", "minecraft:smoker[facing={F:front},lit=true]"]
    for i, x in enumerate(range(-9, 10, 3)):
        put(x, 1, 15, back[i % len(back)])
    put(-7, 1, 15, "BREWER")   # the working Kahve Makinesi (Turkish coffee mod)
    put(4, 1, 15, "minecraft:iron_block"); ENT.append((4, 3.2, 15, "doner", None))  # döner spit
    fill(4, 2, 15, 4, 3, 15, "minecraft:iron_bars")
    for x in (-9, -8, 8, 9):
        fill(x, 1, 14, x, 3, 14, "minecraft:bookshelf" if x in (-9, 9) else "minecraft:barrel[facing={F:front}]")
    # shelves of jars
    for x in range(-6, 7, 2):
        put(x, 4, 15, "minecraft:decorated_pot[facing={F:front}]")
    # chefs (villagers) behind the counter
    for i, x in enumerate((-6, -2, 2, 6)):
        ENT.append((x, 1, 13, "chef", i))
    # big sign above the door
    ENT.append((0, 7.6, -1, "sign", None))

CHEFS = [
    ("Kebapçı Usta",         ["kebap", "kofte", "sokak"],                       "minecraft:butcher"),
    ("Lokantacı Hasan",      ["corba", "ana", "pilav", "deniz", "dolma"],      "minecraft:farmer"),
    ("Fırıncı & Kahvaltıcı", ["hamur", "ekmek", "kahv", "meze"],               "minecraft:fisherman"),
    ("Tatlıcı & Çaycı",      ["tatli", "icecek", "kuru"],                      "minecraft:cleric"),
]

DIRS = {  # forward, right, yaw that faces the player (toward -forward)
    "south": ((0, 1), (-1, 0), 180.0),
    "north": ((0, -1), (1, 0), 0.0),
    "east":  ((1, 0), (0, 1), 90.0),
    "west":  ((-1, 0), (0, -1), -90.0),
}
NAME = {(0, 1): "south", (0, -1): "north", (1, 0): "east", (-1, 0): "west"}

def foods():
    seen, out = set(), []
    for row in tf.F:
        sid = tf.slug(row[0])
        if sid in seen: continue
        seen.add(sid); out.append((row[0], row[1], sid))
    return out

def emit(d):
    f, r, yaw = DIRS[d]
    def w(x, z): return (r[0] * x + f[0] * z, r[1] * x + f[1] * z)
    def face(name):
        v = {"back": f, "front": (-f[0], -f[1]), "right": r, "left": (-r[0], -r[1])}[name]
        return NAME[v]
    def state(s):
        for k in ("front", "back", "left", "right"):
            s = s.replace("{F:%s}" % k, face(k))
        return s
    def tl(v): return "~" if v == 0 else f"~{v}"
    def pos(x, y, z):
        wx, wz = w(x, z)
        return f"{tl(wx)} {tl(y)} {tl(wz)}"
    L = ["# generated by tools/turk_restaurant.py",
         f"kill @e[type=!player,tag=astro_rest,distance=..40]",
         f"fill {pos(-11,1,-6)} {pos(11,20,5)} minecraft:air",
         f"fill {pos(-11,1,6)} {pos(11,20,18)} minecraft:air"]
    for (x, y, z), s in sorted(B.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2])):
        if s == "minecraft:air": continue
        if s == "BREWER":
            L.append(f'setblock {pos(x,y,z)} minecraft:brewing_stand{{CustomName:{{text:"Kahve Makinesi",color:"gold",bold:true}}}}')
            continue
        L.append(f"setblock {pos(x,y,z)} {state(s)}")
    flat = "left_rotation:[-0.7071f,0f,0f,0.7071f],right_rotation:[0f,0f,0f,1f]"
    food = foods(); show = [x for x in food if x[1] in ("kebap", "tatli", "corba", "hamur", "sokak", "kofte")]
    k = 0
    for (x, y, z, kind, data) in ENT:
        wx, wz = w(x, z)
        p = f"~{wx + .5:.2f} ~{y:.2f} ~{wz + .5:.2f}"
        if kind in ("table", "counter", "doner"):
            n, c, sid = show[(k * 7 + 3) % len(show)] if kind != "doner" else next(v for v in food if v[2] == "et_doner")
            k += 1
            item = tf.item_snbt(n, c, sid).replace("count:16", "count:1")
            sc = "0.55f" if kind == "table" else ("0.45f" if kind == "counter" else "1.6f")
            rot = flat if kind == "table" else "left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]"
            bb = '"fixed"' if kind == "table" else '"vertical"'
            L.append(f'summon minecraft:item_display {p} {{Tags:["astro_rest"],item:{item},billboard:{bb},'
                     f'transformation:{{{rot},translation:[0f,0f,0f],scale:[{sc},{sc},{sc}]}}}}')
        elif kind == "sign":
            L.append(f'summon minecraft:text_display {p} {{Tags:["astro_rest"],billboard:"vertical",background:0,shadow:1b,'
                     f'transformation:{{left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],translation:[0f,0f,0f],scale:[3.2f,3.2f,3.2f]}},'
                     f'text:[{{text:"★ ",color:"white"}},{{text:"TÜRK MUTFAĞI",color:"red",bold:true}},{{text:" ★",color:"white"}}]}}')
            L.append(f'summon minecraft:text_display ~{wx + .5:.2f} ~{y-0.9:.2f} ~{wz + .5:.2f} {{Tags:["astro_rest"],billboard:"vertical",background:0,'
                     f'transformation:{{left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],translation:[0f,0f,0f],scale:[1.4f,1.4f,1.4f]}},'
                     f'text:{{text:"Astro SMP • Lokanta • Kebap • Tatlı • Çay",color:"gold"}}}}')
        elif kind == "chef":
            nm, cats, prof = CHEFS[data]
            recipes = []
            for n, c, sid in food:
                if c not in cats: continue
                price = 2 if c in ("kebap", "ana", "deniz") else 1
                item = tf.item_snbt(n, c, sid).replace("count:16", "count:4")
                recipes.append(f'{{buy:{{id:"minecraft:emerald",count:{price}}},sell:{item},maxUses:2147483647,rewardExp:0b,xp:0,priceMultiplier:0f}}')
            if data == 1:
                for key, cnt in (("tabak", 8), ("kasik", 1), ("catal", 1), ("bicak", 1)):
                    recipes.insert(0, f'{{buy:{{id:"minecraft:emerald",count:1}},sell:{tf.tool_snbt(key, cnt)},maxUses:2147483647,rewardExp:0b,xp:0,priceMultiplier:0f}}')
            L.append(f'summon minecraft:villager {p} {{Tags:["astro_rest"],NoAI:1b,Invulnerable:1b,Silent:1b,PersistenceRequired:1b,'
                     f'CustomNameVisible:1b,CustomName:{{text:"{nm}",color:"gold",bold:true}},Rotation:[{yaw}f,0f],'
                     f'VillagerData:{{profession:"{prof}",level:5,type:"minecraft:plains"}},Offers:{{Recipes:[{",".join(recipes)}]}}}}')
    L.append('particle minecraft:happy_villager ~ ~3 ~ 6 3 6 0 200 force')
    L.append('playsound minecraft:ui.toast.challenge_complete master @a ~ ~ ~ 2 1')
    clear = ["# generated by tools/turk_restaurant.py",
             f"kill @e[type=!player,tag=astro_rest,distance=..40]",
             f"fill {pos(-11,1,-6)} {pos(11,20,5)} minecraft:air",
             f"fill {pos(-11,1,6)} {pos(11,20,18)} minecraft:air",
             f"fill {pos(-11,0,-6)} {pos(11,0,18)} minecraft:grass_block",
             "playsound minecraft:entity.generic.explode master @a ~ ~ ~ 2 0.8",
             "particle minecraft:cloud ~ ~3 ~ 8 3 8 0.05 300 force"]
    return L, clear

def main():
    build()
    out = os.path.join(ROOT, "src", "main", "resources", "data", "astro_staff", "function", "turk")
    os.makedirs(out, exist_ok=True)
    for d in DIRS:
        L, C = emit(d)
        open(os.path.join(out, f"rest_build_{d}.mcfunction"), "w", encoding="utf-8").write("\n".join(L) + "\n")
        open(os.path.join(out, f"rest_clear_{d}.mcfunction"), "w", encoding="utf-8").write("\n".join(C) + "\n")
    print(f"restaurant: {len(B)} blocks, {len(ENT)} entities")

if __name__ == "__main__":
    main()
