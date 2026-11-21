#!/usr/bin/env python3
"""Astro Mutfak (kitchen) generator. Run AFTER turk_food.py and turk_restaurant.py.
Outputs:
  src/main/resources/astro_recipes.txt                      (vessel|keys|seconds|name|ingredients|give-item)
  src/main/resources/data/astro_staff/function/turk/kitchen_build_<dir>.mcfunction / kitchen_clear_<dir>.mcfunction
  build/astro_food_pack.zip  (re-written: adds ingredient / vessel / world-food icons) + astro_pack.txt sha1
"""
import hashlib, io, json, os, re, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import turk_food as tf

ROOT = tf.ROOT
Img, rgb, shade, mix = tf.Img, tf.rgb, tf.shade, tf.mix

# ============================================================================ ingredients
# key -> (name, shape, colour a, colour b)
ING = {
    "un": ("Un", "sack", "f4efe2", "d8c8a0"), "tuz": ("Tuz", "sack", "fafafa", "9ab0c8"),
    "pul_biber": ("Pul Biber", "jar", "c4301c", "f0e0c0"), "karabiber": ("Karabiber", "jar", "3a3a3a", "d0d0d0"),
    "kimyon": ("Kimyon", "jar", "a8782a", "f0e0c0"), "nane_kuru": ("Kuru Nane", "jar", "6a8a3a", "f0e0c0"),
    "domates": ("Domates", "veg_round", "d8302a", "4f9a3a"), "sogan": ("Soğan", "veg_round", "e8c890", "8a5a2a"),
    "sarimsak": ("Sarımsak", "veg_round", "f4f0e6", "c8c0b0"), "limon": ("Limon", "veg_round", "f6e040", "c8b020"),
    "portakal": ("Portakal", "veg_round", "f8a020", "4f9a3a"), "nar": ("Nar", "veg_round", "b81a2a", "e8c040"),
    "biber": ("Yeşil Biber", "veg_long", "4f9a3a", "2a6a2a"), "kirmizi_biber": ("Kırmızı Biber", "veg_long", "c4301c", "4f9a3a"),
    "patlican": ("Patlıcan", "veg_long", "4a2a5a", "4f9a3a"), "kabak": ("Kabak", "veg_long", "8ab04a", "c8d88a"),
    "salatalik": ("Salatalık", "veg_long", "4a8a3a", "a8c870"), "maydanoz": ("Maydanoz", "leaf", "4f9a3a", "2a6a2a"),
    "nane": ("Nane", "leaf", "6ab84a", "3a7a2a"), "ispanak": ("Ispanak", "leaf", "3a6a2a", "5a8a3a"),
    "marul": ("Marul", "leaf", "8ac84a", "5a9a3a"), "cay": ("Çay Yaprağı", "leaf", "3a4a2a", "6a5a2a"),
    "pirinc": ("Pirinç", "grain", "f6f4ec", "e6e0d0"), "bulgur": ("Bulgur", "grain", "c8963a", "a87a2a"),
    "mercimek": ("Kırmızı Mercimek", "grain", "e8892b", "c8701b"), "nohut": ("Nohut", "grain", "e8c870", "c8a050"),
    "fasulye": ("Kuru Fasulye", "grain", "f2e6cc", "d8c8a8"), "makarna": ("Makarna", "pasta", "f2d070", "d8b050"),
    "sehriye": ("Şehriye", "pasta", "f0c860", "d8a840"), "yogurt": ("Yoğurt", "cup", "f8f8f4", "e8e8e0"),
    "peynir": ("Beyaz Peynir", "cheese", "f8f6ee", "e0dccc"), "kasar": ("Kaşar", "cheese", "f6d860", "e0b830"),
    "tereyagi": ("Tereyağı", "cheese", "f6e070", "e8c840"), "zeytinyagi": ("Zeytinyağı", "bottle", "c8b830", "6a8a2a"),
    "salca": ("Salça", "jar", "b8241a", "e8e0d0"), "kiyma": ("Kıyma", "meat", "b8463a", "e8a090"),
    "sucuk_ham": ("Çiğ Sucuk", "sausage", "9b2a1a", "f2e0c0"), "fistik": ("Antep Fıstığı (iç)", "grain", "8ab04a", "c8a870"),
    "ceviz_ic": ("Ceviz İçi", "grain", "b88a5a", "7a5a3a"), "findik_ic": ("Fındık İçi", "grain", "c8904a", "9a6a3a"),
    "irmik": ("İrmik", "sack", "f0d890", "d8c070"), "nisasta": ("Nişasta", "sack", "fcfcfa", "e0e0e0"),
    "kahve": ("Kahve Çekirdeği", "grain", "4a2a1a", "6a4a2a"), "hamur": ("Hamur", "dough", "f2e2c0", "e0c898"),
    "yufka": ("Yufka", "round_flat", "f4e8c8", "d8c090"), "karides": ("Karides", "shrimp", "f08060", "f8c0a0"),
    "midye": ("Midye", "mussel_raw", "2a2a3a", "e8902a"), "kalamar": ("Kalamar", "rings_raw", "f2ece0", "d8d0c0"),
    "zeytin": ("Zeytin", "grain", "2a1e2a", "5a4a5a"), "maya": ("Maya", "sack", "e8d8a0", "c8b070"),
    "kaymak": ("Kaymak", "cup", "fbf6e8", "f2e8c8"), "pekmez": ("Pekmez", "jar", "5a2a1a", "e8e0d0"),
    "tahin": ("Tahin", "jar", "d8c8a8", "e8e0d0"), "vanilya": ("Vanilya", "jar", "f2ecd8", "3a2a1a"),
    "kakao_tozu": ("Kakao Tozu", "sack", "5a3a1a", "3a2a1a"), "cikolata": ("Çikolata", "bar", "5a3a1a", "3a2414"),
    "krema": ("Krema", "cup", "fbfbf6", "f0ece0"), "mantar": ("Kültür Mantarı", "veg_round", "e8e0d0", "a8907a"),
    "misir": ("Mısır Koçanı", "veg_long", "f6d030", "6a9a3a"), "bezelye": ("Bezelye", "grain", "6ab84a", "4a9a3a"),
    "bamya": ("Bamya", "veg_long", "5a8a2a", "3a6a2a"), "pirasa": ("Pırasa", "veg_long", "c8d888", "5a9a3a"),
    "lahana": ("Lahana", "veg_round", "b8c890", "8aa860"), "asma_yapragi": ("Asma Yaprağı", "leaf", "4a6a2a", "6a8a3a"),
    "kayisi": ("Kayısı", "veg_round", "f09a30", "e8802a"), "incir": ("İncir", "veg_round", "6a3a4a", "c8a070"),
    "uzum": ("Üzüm", "grain", "5a2a5a", "8a4a8a"), "gul": ("Gül Yaprağı", "leaf", "e86a9a", "c84a7a"),
}
VAN = {  # vanilla items players can use as ingredients
    "minecraft:egg": "Yumurta", "minecraft:milk_bucket": "Süt", "minecraft:sugar": "Şeker", "minecraft:honey_bottle": "Bal",
    "minecraft:bread": "Ekmek", "minecraft:beef": "Dana Eti", "minecraft:chicken": "Tavuk", "minecraft:mutton": "Kuzu Eti",
    "minecraft:cod": "Balık", "minecraft:salmon": "Somon", "minecraft:potato": "Patates", "minecraft:carrot": "Havuç",
    "minecraft:apple": "Elma", "minecraft:cocoa_beans": "Kakao", "minecraft:wheat": "Buğday", "minecraft:brown_mushroom": "Mantar",
    "minecraft:sweet_berries": "Vişne", "minecraft:pumpkin": "Balkabağı", "minecraft:melon_slice": "Kavun", "minecraft:beetroot": "Pancar",
    "minecraft:kelp": "Deniz Yosunu", "su": "Su",
}
VESSELS = {
    "tava": ("Tava", "Kızartma / sote / krep", 6, True), "tencere": ("Tencere", "Çorba / haşlama / güveç", 10, True),
    "tepsi": ("Fırın Tepsisi", "Fırında pişenler", 8, True), "tahta": ("Kesme Tahtası", "Doğrama / karıştırma (ateş gerekmez)", 3, False),
    "cezve": ("Cezve", "Kahve / sıcak içecekler", 5, True),
}

def ing_name(k):
    if k.startswith("ing:"): return ING[k[4:]][0]
    if k.startswith("food:"): return FOODNAME.get(k[5:], k[5:])
    return VAN[k]

def ing_give(key, color="white"):
    n = ING[key][0]
    return (f'minecraft:paper[custom_name={{text:"{tf.esc(n)}",color:"{color}",italic:false}},'
            f'lore=[{{text:"Malzeme • Tencereye/tavaya koy",color:"gray",italic:false}}],'
            f'custom_model_data={{strings:["ing_{key}"]}},custom_data={{astro_ing:"{key}"}}]')
def ing_nbt(key, count):
    n = ING[key][0]
    return (f'{{id:"minecraft:paper",count:{count},components:{{"minecraft:custom_name":{{text:"{tf.esc(n)}",color:"white",italic:false}},'
            f'"minecraft:lore":[{{text:"Malzeme • Tencereye/tavaya koy",color:"gray",italic:false}}],'
            f'"minecraft:custom_model_data":{{strings:["ing_{key}"]}},"minecraft:custom_data":{{astro_ing:"{key}"}}}}}}')
def vessel_nbt(v, count=1):
    n, lore, _, heat = VESSELS[v]
    l2 = "Shift + sağ tık: Ocak'ın üstüne koy" if heat else "Shift + sağ tık: tezgaha koy"
    return (f'{{id:"minecraft:bowl",count:{count},components:{{"minecraft:custom_name":{{text:"{tf.esc(n)}",color:"gold",bold:true,italic:false}},'
            f'"minecraft:lore":[{{text:"{tf.esc(lore)}",color:"gray",italic:false}},{{text:"{tf.esc(l2)}",color:"dark_gray",italic:false}}],'
            f'"minecraft:custom_model_data":{{strings:["v_{v}"]}},"minecraft:custom_data":{{astro_vessel:"{v}"}}}}}}')
OCAK_NBT = ('{id:"minecraft:smoker",count:1,components:{"minecraft:custom_name":{text:"Ocak",color:"gold",bold:true,italic:false},'
            '"minecraft:lore":[{text:"Tava / tencere / tepsi / cezveyi üstüne koy",color:"gray",italic:false}]}}')

def food_give(name, cat, sid, cats):
    label, base, nut, sat, _, color, rem = cats[cat]
    drink = cat == "icecek"
    s = (f'minecraft:{base}[custom_name={{text:"{tf.esc(name)}",color:"{color}",bold:true,italic:false}},'
         f'lore=[{{text:"{tf.esc(label)}",color:"gray",italic:false}},{{text:"Astro Mutfak • Ev yapımı",color:"dark_gray",italic:true}}],'
         f'custom_model_data={{strings:["{sid}"]}},custom_data={{astro_food:"{sid}"}},max_stack_size=64,'
         f'food={{nutrition:{nut + 1},saturation:{sat + 1}f,can_always_eat:{"true" if drink else "false"}}},'
         f'consumable={{consume_seconds:{"1.2" if drink else "1.6"}f,animation:"{"drink" if drink else "eat"}",'
         f'sound:"minecraft:{"entity.generic.drink" if drink else "entity.generic.eat"}",has_consume_particles:{"false" if drink else "true"}}}')
    if rem: s += f',use_remainder={{id:"minecraft:{rem}",count:1}}'
    return s + "]"

# ============================================================================ world foods (new)
CATS = dict(tf.CATS)
CATS["dunya"] = ("Dünya Mutfağı", "cooked_rabbit", 7, 8.0, "plate", "light_purple", None)
WORLD = [
    ("Pankek", "dunya", "e8b050", "f6c030", "pancake"), ("Krep", "dunya", "f2d890", "5a3a1a", "round"),
    ("Omlet", "dunya", "f6d040", "4f9a3a", "pan"), ("Sahanda Yumurta", "dunya", "f8f6f0", "f6c020", "pan"),
    ("Peynirli Omlet", "dunya", "f6d040", "f6f2e8", "pan"), ("Mantarlı Omlet", "dunya", "f6d040", "a8907a", "pan"),
    ("Patates Kızartması", "dunya", "f6d050", "d8402a", "fries"), ("Fırın Patates", "dunya", "c8984a", "6a9a3a", "plate"),
    ("Patates Püresi", "dunya", "f6ecc0", "f6e070", "bowl"), ("Pizza", "dunya", "e8b060", "d8302a", "lahmacun"),
    ("Hamburger", "dunya", "c88a4a", "6a3a1a", "burger"), ("Waffle", "dunya", "e8b050", "5a3a1a", "toast"),
    ("Kek", "dunya", "e8c070", "5a3a1a", "slice"), ("Çikolatalı Kek", "dunya", "5a3a1a", "f2e2b8", "slice"),
    ("Cheesecake", "dunya", "f6ecc8", "b81a2a", "slice"), ("Brownie", "dunya", "4a2a14", "6a4a2a", "toast"),
    ("Sufle", "dunya", "4a2a14", "f6f2e8", "pudding"), ("Sıcak Çikolata", "icecek", "5a3a1a", "f6f2e8", "cup"),
    ("Sütlü Kakao", "icecek", "8a5a3a", "f6f2e8", "cup"), ("Meyve Salatası", "dunya", "d8402a", "f6d040", "bowl"),
    ("Elmalı Turta", "dunya", "e8b050", "c8301c", "slice"), ("Balkabağı Çorbası", "corba", "f08a20", "f6f0e0", "bowl"),
    ("Mantar Sote", "dunya", "a8907a", "4f9a3a", "pot"), ("Sebzeli Makarna", "pilav", "f2d070", "4f9a3a", "noodles"),
    ("Kremalı Makarna", "pilav", "f6ecd0", "f6f2e8", "noodles"), ("Lazanya", "dunya", "e8b050", "c8301c", "slice"),
    ("Tavuk Nugget", "dunya", "d89a3a", "f2d080", "balls"), ("Fırında Somon", "deniz", "f08a5a", "f6f0e0", "fish"),
    ("Karnabahar Kızartması", "dunya", "f2e2b0", "c8984a", "balls"), ("Tost Ekmeği", "dunya", "e0a848", "f6e8c0", "toast"),
    ("Kızarmış Ekmek", "dunya", "c8843a", "f6e070", "toast"), ("Ballı Ekmek", "dunya", "e0a848", "f6b020", "toast"),
    ("Yumurtalı Ekmek", "dunya", "e8b050", "f6d040", "toast"), ("Haşlanmış Patates", "dunya", "e8c070", "f6f0e0", "plate"),
    ("Haşlanmış Mısır Tabağı", "dunya", "f6d030", "f6f0e0", "corn"), ("Tavuk Sote Wrap", "sokak", "f2e2b8", "e0a050", "wrap"),
    ("Popcorn", "dunya", "fbf6e0", "f6e070", "nuts"), ("Karamelli Puding", "dunya", "f0c060", "8a5a2a", "pudding"),
    ("Smoothie", "icecek", "e8608a", "f8f0f6", "glass"), ("Milkshake", "icecek", "f8d8e8", "f8f8f8", "glass"),
    ("Ev Yapımı Limonata", "icecek", "f6e870", "6ab84a", "glass"), ("Ev Yapımı Ayran", "icecek", "f8f8f4", "ffffff", "ayran"),
]

# ============================================================================ recipe generation
RULES = [  # (regex on food name, ingredients)
    (r"Mercimek", ["ing:mercimek", "ing:sogan"]), (r"Ezogelin", ["ing:mercimek", "ing:bulgur", "ing:salca"]),
    (r"Yayla", ["ing:yogurt", "ing:pirinc", "ing:nane_kuru"]), (r"Tarhana", ["ing:yogurt", "ing:un", "ing:domates"]),
    (r"İşkembe|Kelle|Paça", ["minecraft:mutton", "ing:sarimsak"]), (r"Domates", ["ing:domates"]),
    (r"Tavuk|Çerkez", ["minecraft:chicken"]), (r"Kuzu|Tandır|Kelle|Testi|Kaburga", ["minecraft:mutton"]),
    (r"Balık|Hamsi|Levrek|Çipura|Lüfer|Palamut|Uskumru|Lakerda", ["minecraft:cod"]), (r"Somon", ["minecraft:salmon"]),
    (r"Karides", ["ing:karides"]), (r"Midye", ["ing:midye"]), (r"Kalamar", ["ing:kalamar"]),
    (r"Köfte|Adana|Urfa|Beyti|Lahmacun|Kıymalı|Etli Ekmek|Karnıyarık|Mantı|Musakka|Hingel|Islak", ["ing:kiyma"]),
    (r"Şiş|Kuşbaşı|Döner|Et |Sote|Kavurma|Tas Kebab|Orman|Güveç|Kağıt|Cağ|Hünkar|Tirit|Söğüş|Tantuni|Keşkek|Pirzola|İskender", ["minecraft:beef"]),
    (r"Ciğer|Kokoreç|Mumbar", ["minecraft:mutton"]), (r"Patlıcan|Karnıyarık|İmam|Babagannuş|Şakşuka|Alinazik|Hünkar|Musakka", ["ing:patlican"]),
    (r"Biber", ["ing:biber"]), (r"Kabak|Mücver", ["ing:kabak"]), (r"Ispanak", ["ing:ispanak"]), (r"Bamya", ["ing:bamya"]),
    (r"Pırasa", ["ing:pirasa"]), (r"Kereviz|Enginar|Semizotu|Börülce", ["ing:marul"]), (r"Lahana|Kapuska", ["ing:lahana"]),
    (r"Yaprak|Sarma", ["ing:asma_yapragi"]), (r"Fasulye|Piyaz|Barbunya", ["ing:fasulye"]), (r"Nohut|Humus|Leblebi", ["ing:nohut"]),
    (r"Pilav|Sütlaç|Dolma|Zerde|Pirinç", ["ing:pirinc"]), (r"Bulgur|Kısır|Çiğ Köfte|İçli|Firik", ["ing:bulgur"]),
    (r"Makarna|Spagetti|Lazanya", ["ing:makarna"]), (r"Şehriye", ["ing:sehriye"]), (r"Erişte", ["ing:hamur"]),
    (r"Yumurta|Menemen|Omlet|Çılbır|Krep|Pankek|Kek|Waffle|Sufle|Revani", ["minecraft:egg"]),
    (r"Menemen|Çoban|Ezme|Gavurdağı|Güveç|Türlü|Musakka|İzmir", ["ing:domates"]),
    (r"Peynir|Kaşar|Lor|Tulum|Pizza|Cheesecake|Mıhlama|Gözleme|Pide|Börek|Künefe|Hellim", ["ing:peynir"]),
    (r"Kaşar|Pizza|Tost|Mıhlama", ["ing:kasar"]), (r"Yoğurt|Cacık|Haydari|Ayran|Alinazik|Kefir|İskender", ["ing:yogurt"]),
    (r"Süt|Sütlaç|Muhallebi|Kazandibi|Tavuk Göğsü|Keşkül|Güllaç|Trileçe|Sahlep|Milkshake|Kakao|Krep|Pankek|Supangle|Puding|Püre", ["minecraft:milk_bucket"]),
    (r"Bal|Pankek|Lokma", ["minecraft:honey_bottle"]), (r"Tatlı|Baklava|Revani|Şekerpare|Helva|Lokum|Lokma|Tulumba|Kadayıf|Sütlaç|Muhallebi|Kek|Pişmaniye|Cezerye|Şerbet|Limonata|Kurabiye|Waffle|Pasta|Turta|Puding|Zerde|Aşure|Höşmerim", ["minecraft:sugar"]),
    (r"Çikolata|Brownie|Profiterol|Supangle|Kakao|San Sebastian|Tiramisu", ["ing:cikolata"]),
    (r"Fıstık|Baklava|Katmer|Şöbiyet|Burma|Saray", ["ing:fistik"]), (r"Ceviz", ["ing:ceviz_ic"]), (r"Fındık", ["ing:findik_ic"]),
    (r"Elma|Turta", ["minecraft:apple"]), (r"Ayva", ["minecraft:apple"]), (r"Patates|Kumpir|Püre", ["minecraft:potato"]),
    (r"Havuç|Rus Salata", ["minecraft:carrot"]), (r"Mantar", ["ing:mantar"]), (r"Kayısı", ["ing:kayisi"]), (r"İncir", ["ing:incir"]),
    (r"Limon|Limonata", ["ing:limon"]), (r"Portakal", ["ing:portakal"]), (r"Nar", ["ing:nar"]), (r"Vişne", ["minecraft:sweet_berries"]),
    (r"Gül", ["ing:gul"]), (r"Üzüm|Pestil|Pekmez", ["ing:uzum"]), (r"Çay", ["ing:cay"]), (r"Kahve", ["ing:kahve"]),
    (r"Tahin|Humus|Helva", ["ing:tahin"]), (r"Pekmez", ["ing:pekmez"]), (r"Kaymak|Ekmek Kadayıfı", ["ing:kaymak"]),
    (r"Sucuk", ["ing:sucuk_ham"]), (r"Pastırma", ["minecraft:beef", "ing:kimyon"]), (r"Zeytin", ["ing:zeytin"]),
    (r"Mısır", ["ing:misir"]), (r"Bezelye", ["ing:bezelye"]), (r"Balkabağı|Kabak Tatlısı", ["minecraft:pumpkin"]),
    (r"Pancar", ["minecraft:beetroot"]), (r"Salatalık|Cacık|Çoban", ["ing:salatalik"]), (r"Maydanoz|Kısır|Tabule", ["ing:maydanoz"]),
    (r"Nane", ["ing:nane"]), (r"Smoothie|Meyve", ["minecraft:sweet_berries", "minecraft:apple"]), (r"Kavun", ["minecraft:melon_slice"]),
    (r"Hamburger|Kumru|Balık Ekmek|Tost|Ekmeği|Kızarmış Ekmek|Ballı Ekmek|Yumurtalı Ekmek", ["minecraft:bread"]),
    (r"Nugget|Karnabahar", ["ing:un"]), (r"Popcorn", ["ing:misir"]), (r"Boza", ["minecraft:wheat"]), (r"Şalgam", ["minecraft:carrot", "minecraft:beetroot"]),
    (r"Soda|Maden Suyu", ["ing:limon"]),
]
STAPLE = {  # what each category always needs
    "corba": ["su"], "kebap": ["ing:tuz"], "kofte": ["ing:sogan"], "hamur": ["ing:hamur"], "ekmek": ["ing:un", "ing:maya"],
    "kahv": [], "meze": ["ing:zeytinyagi"], "dolma": ["ing:zeytinyagi"], "ana": ["ing:sogan"], "pilav": ["ing:tereyagi"],
    "deniz": ["ing:limon"], "sokak": ["ing:yufka"], "tatli": ["minecraft:sugar"], "icecek": ["su"], "kuru": ["ing:tuz"],
    "dunya": [],
}
EXTRA = ["ing:tuz", "ing:karabiber", "ing:pul_biber", "ing:maydanoz", "ing:sogan", "ing:sarimsak", "ing:kimyon",
         "ing:zeytinyagi", "ing:tereyagi", "ing:limon", "ing:nane_kuru", "ing:salca", "minecraft:sugar", "ing:vanilya"]

def vessel_for(name, cat):
    if re.search(r"Kahvesi|Sahlep|Sıcak Çikolata|Kakao|Boza", name): return "cezve"
    if cat == "icecek":
        return "tencere" if re.search(r"Çay|Ihlamur|Ada|Elma Çay|Kuşburnu|Nane Limon|Süt", name) else "tahta"
    if cat in ("corba", "ana", "pilav", "dolma"): return "tencere"
    if cat in ("hamur", "ekmek"): return "tepsi"
    if cat == "tatli":
        if re.search(r"Dondurma|Lokum|Cezerye|Pişmaniye|Güllaç|Kazan Dibi Dondurmal", name): return "tahta"
        if re.search(r"Sütlaç|Muhallebi|Keşkül|Supangle|Aşure|Zerde|Helva|Höşmerim|Tavuk Göğsü|Kazandibi", name): return "tencere"
        if re.search(r"Lokma|Tulumba|Pişi|Kemalpaşa", name): return "tava"
        return "tepsi"
    if cat == "meze": return "tava" if re.search(r"Közlenmiş|Şakşuka|Mücver|Babagannuş", name) else "tahta"
    if cat == "kahv": return "tahta" if re.search(r"Peynir|Zeytin|Bal Kaymak|Tahin|Tabağı|Lor|Tulum", name) else "tava"
    if cat == "kuru": return "tava" if re.search(r"Kavrulmuş|Kestane|Leblebi|Çekirde|Popcorn", name) else "tahta"
    if cat == "dunya":
        if re.search(r"Kek|Brownie|Turta|Lazanya|Pizza|Cheesecake|Fırın|Sufle", name): return "tepsi"
        if re.search(r"Püre|Haşlanmış|Puding|Çorba", name): return "tencere"
        if re.search(r"Salata|Meyve", name): return "tahta"
        return "tava"
    if re.search(r"Fırın|Tandır|Testi|Kiremit|Kuyu|Kağıt|Elbasan|Güveç", name): return "tepsi"
    return "tava"

HAND = [  # hand-written showcase recipes (vessel, ingredients, result name)
    ("tava", ["minecraft:honey_bottle", "minecraft:bread"], "Pankek"),
    ("tava", ["minecraft:egg", "minecraft:milk_bucket", "ing:un"], "Krep"),
    ("tava", ["minecraft:egg", "minecraft:egg", "ing:tuz"], "Omlet"),
    ("tava", ["minecraft:egg", "ing:tereyagi"], "Sahanda Yumurta"),
    ("tava", ["minecraft:egg", "minecraft:egg", "ing:peynir"], "Peynirli Omlet"),
    ("tava", ["minecraft:egg", "minecraft:egg", "ing:mantar"], "Mantarlı Omlet"),
    ("tava", ["minecraft:potato", "ing:zeytinyagi", "ing:tuz"], "Patates Kızartması"),
    ("tava", ["minecraft:egg", "ing:domates", "ing:biber"], "Menemen"),
    ("tava", ["minecraft:egg", "ing:sucuk_ham"], "Sucuklu Yumurta"),
    ("tava", ["minecraft:bread"], "Kızarmış Ekmek"),
    ("tahta", ["minecraft:bread", "minecraft:honey_bottle"], "Ballı Ekmek"),
    ("tava", ["minecraft:bread", "minecraft:egg"], "Yumurtalı Ekmek"),
    ("tava", ["minecraft:bread", "ing:kasar"], "Kaşarlı Tost"),
    ("tava", ["minecraft:bread", "ing:kasar", "ing:sucuk_ham"], "Sucuklu Tost"),
    ("tahta", ["ing:yogurt", "su", "ing:tuz"], "Ayran"),
    ("tahta", ["ing:yogurt", "su"], "Ev Yapımı Ayran"),
    ("tahta", ["ing:limon", "minecraft:sugar", "su"], "Limonata"),
    ("tahta", ["ing:limon", "minecraft:sugar", "su", "ing:nane"], "Ev Yapımı Limonata"),
    ("tencere", ["ing:cay", "su"], "Türk Çayı"),
    ("cezve", ["ing:kahve", "su"], "Türk Kahvesi Fincanı"),
    ("cezve", ["ing:kahve", "su", "minecraft:sugar"], "Dibek Kahvesi"),
    ("cezve", ["ing:cikolata", "minecraft:milk_bucket"], "Sıcak Çikolata"),
    ("cezve", ["minecraft:cocoa_beans", "minecraft:milk_bucket", "minecraft:sugar"], "Sütlü Kakao"),
    ("tencere", ["ing:mercimek", "ing:sogan", "su"], "Mercimek Çorbası"),
    ("tencere", ["ing:pirinc", "su", "ing:tereyagi"], "Pirinç Pilavı"),
    ("tencere", ["ing:bulgur", "su", "ing:salca"], "Bulgur Pilavı"),
    ("tencere", ["ing:makarna", "su", "ing:salca"], "Spagetti"),
    ("tencere", ["minecraft:milk_bucket", "ing:pirinc", "minecraft:sugar"], "Sütlaç"),
    ("tencere", ["minecraft:potato", "minecraft:milk_bucket", "ing:tereyagi"], "Patates Püresi"),
    ("tepsi", ["ing:un", "minecraft:egg", "minecraft:sugar", "minecraft:milk_bucket"], "Kek"),
    ("tepsi", ["ing:un", "minecraft:egg", "minecraft:sugar", "ing:cikolata"], "Çikolatalı Kek"),
    ("tepsi", ["ing:hamur", "ing:domates", "ing:kasar"], "Pizza"),
    ("tepsi", ["ing:yufka", "ing:fistik", "minecraft:sugar", "ing:tereyagi"], "Baklava"),
    ("tepsi", ["ing:hamur", "ing:kiyma", "ing:domates"], "Lahmacun"),
    ("tava", ["ing:kiyma", "ing:sogan", "ing:tuz"], "Izgara Köfte"),
    ("tava", ["ing:kiyma", "ing:pul_biber", "ing:tuz"], "Adana Kebap"),
    ("tava", ["minecraft:bread", "ing:kiyma", "ing:domates"], "Hamburger"),
    ("tahta", ["minecraft:sweet_berries", "minecraft:milk_bucket", "minecraft:sugar"], "Milkshake"),
    ("tahta", ["minecraft:sweet_berries", "minecraft:apple", "ing:yogurt"], "Smoothie"),
    ("tahta", ["ing:domates", "ing:salatalik", "ing:sogan", "ing:limon"], "Çoban Salatası"),
    ("tahta", ["ing:yogurt", "ing:salatalik", "ing:sarimsak", "su"], "Cacık"),
]
PROCESS = [  # basic prep recipes that produce ingredients (vessel, ingredients, result ing, count)
    ("tahta", ["minecraft:wheat", "minecraft:wheat", "minecraft:wheat"], "un", 3),
    ("tahta", ["ing:un", "su"], "hamur", 2), ("tahta", ["ing:un", "su", "ing:maya"], "hamur", 4),
    ("tahta", ["ing:hamur"], "yufka", 2), ("tahta", ["minecraft:beef"], "kiyma", 2), ("tahta", ["minecraft:mutton"], "kiyma", 2),
    ("tahta", ["minecraft:milk_bucket"], "tereyagi", 2), ("tencere", ["minecraft:milk_bucket", "ing:limon"], "peynir", 2),
    ("tencere", ["minecraft:milk_bucket", "ing:yogurt"], "yogurt", 4), ("tencere", ["minecraft:milk_bucket"], "kaymak", 2),
    ("tepsi", ["ing:peynir"], "kasar", 1), ("tencere", ["minecraft:wheat", "su"], "bulgur", 3),
    ("tava", ["minecraft:wheat"], "irmik", 2), ("tahta", ["minecraft:cocoa_beans", "minecraft:cocoa_beans"], "kakao_tozu", 2),
    ("tahta", ["ing:kakao_tozu", "minecraft:sugar", "minecraft:milk_bucket"], "cikolata", 3),
    ("tahta", ["minecraft:beef", "ing:kimyon", "ing:pul_biber"], "sucuk_ham", 3),
    ("tencere", ["ing:uzum", "ing:uzum"], "pekmez", 2), ("tava", ["ing:kahve"], "kahve", 2),
    ("tahta", ["minecraft:brown_mushroom"], "mantar", 2), ("tahta", ["minecraft:sweet_berries", "minecraft:sweet_berries"], "nar", 1),
    ("tahta", ["minecraft:apple", "minecraft:sugar"], "kayisi", 1), ("tahta", ["ing:findik_ic", "minecraft:sugar"], "tahin", 1),
    ("tencere", ["ing:nohut", "su"], "nohut", 3), ("tencere", ["ing:fasulye", "su"], "fasulye", 3),
    ("tahta", ["minecraft:kelp"], "asma_yapragi", 2), ("tencere", ["ing:domates", "ing:domates", "ing:tuz"], "salca", 2),
    ("tahta", ["minecraft:carrot", "minecraft:carrot"], "biber", 1), ("tahta", ["minecraft:beetroot", "minecraft:beetroot"], "domates", 2),
    ("tahta", ["minecraft:potato", "minecraft:potato"], "sogan", 2), ("tahta", ["minecraft:wheat", "minecraft:wheat"], "pirinc", 2),
]

FOODNAME = {}

def build_recipes():
    foods = []
    seen = set()
    for row in tf.F:
        sid = tf.slug(row[0])
        if sid in seen: continue
        seen.add(sid); foods.append((row[0], row[1], sid))
    for row in WORLD:
        sid = tf.slug(row[0])
        if sid in seen: continue
        seen.add(sid); foods.append((row[0], row[1], sid))
    for n, c, s in foods: FOODNAME[s] = n
    by_name = {n: (n, c, s) for n, c, s in foods}
    out, used = [], set()

    def add(vessel, keys, result_name, give, human=None, alt=False):
        keys = sorted(keys)
        k = vessel + "|" + ",".join(keys)
        tries = 0
        while k in used and tries < len(EXTRA):
            extra = EXTRA[tries]; tries += 1
            if extra in keys or len(keys) >= 6: continue
            keys = sorted(keys + [extra]); k = vessel + "|" + ",".join(keys)
        if k in used: return False
        used.add(k)
        sec = VESSELS[vessel][2] + (2 if len(keys) > 3 else 0)
        h = human or " + ".join(ing_name(x) for x in keys)
        out.append((vessel, ",".join(keys), sec, result_name + (" (alternatif)" if alt else ""), h, give))
        return True

    for v, keys, rn in HAND:
        n, c, s = by_name[rn]
        add(v, keys, n, food_give(n, c, s, CATS))
    for v, keys, ik, cnt in PROCESS:
        add(v, keys, ING[ik][0] + (f" x{cnt}" if cnt > 1 else ""), ing_give(ik) + (f" {cnt}" if cnt > 1 else ""))
    hand_names = {h[2] for h in HAND}
    for n, c, s in foods:
        if n in hand_names: continue
        keys = []
        for rx, ks in RULES:
            if re.search(rx, n):
                for kk in ks:
                    if kk not in keys: keys.append(kk)
        for kk in STAPLE.get(c, []):
            if kk not in keys: keys.append(kk)
        if len(keys) < 2:
            for kk in ("ing:tuz", "ing:sogan") if c not in ("tatli", "icecek") else ("minecraft:sugar", "su"):
                if kk not in keys: keys.append(kk)
                if len(keys) >= 2: break
        keys = keys[:6]
        v = vessel_for(n, c)
        add(v, keys, n, food_give(n, c, s, CATS))
    # alternative versions of every dish
    for n, c, s in foods:
        base = [r for r in out if r[3] == n]
        if not base: continue
        keys = base[0][1].split(",")
        if "ing:zeytinyagi" in keys: alt = [("ing:tereyagi" if x == "ing:zeytinyagi" else x) for x in keys]
        elif "ing:tereyagi" in keys: alt = [("ing:zeytinyagi" if x == "ing:tereyagi" else x) for x in keys]
        elif "minecraft:beef" in keys: alt = [("ing:kiyma" if x == "minecraft:beef" else x) for x in keys]
        elif "minecraft:sugar" in keys and "minecraft:honey_bottle" not in keys: alt = [("minecraft:honey_bottle" if x == "minecraft:sugar" else x) for x in keys]
        else: alt = keys + (["ing:maydanoz"] if c not in ("tatli", "icecek", "kuru") else ["ing:vanilya"])
        add(base[0][0], alt[:6], n, food_give(n, c, s, CATS), alt=True)
    return out, foods

# ============================================================================ icons
def draw_extra(shape, a, b, seed):
    im = Img(seed)
    la, da = mix(a, (255, 255, 255), .35), shade(a, .7)
    if shape == "sack":
        im.ellipse(8, 10, 6, 5, (196, 160, 110), dark=(160, 125, 80)); im.rect(5, 3, 10, 6, (196, 160, 110))
        im.rect(6, 2, 9, 2, (140, 100, 60)); im.ellipse(8, 5.5, 3.2, 1.4, a, light=la); im.rect(5, 9, 10, 11, a)
    elif shape == "veg_round":
        im.ellipse(8, 9, 6, 5.5, a, light=la, dark=da); im.rect(7, 2, 8, 4, b); im.rect(9, 3, 10, 3, b)
    elif shape == "veg_long":
        for i in range(10):
            im.ellipse(4 + i, 12 - i, 2.3, 2.3, a, light=la, dark=da)
        im.rect(13, 1, 14, 3, b)
    elif shape == "leaf":
        for k, (cx, cy) in enumerate(((6, 9), (10, 8), (8, 5))):
            im.ellipse(cx, cy, 3, 4.2, a if k != 1 else b, light=la)
        im.rect(7, 11, 8, 14, (90, 130, 60))
    elif shape == "grain":
        im.ellipse(8, 10.5, 6.6, 3.8, (150, 100, 60), dark=(110, 70, 40)); im.ellipse(8, 9.2, 5.4, 2.4, a, light=la)
        im.speckle(14, b, (3, 7, 13, 11), 3)
    elif shape == "pasta":
        for i in range(6): im.rect(3 + i, 3 + i, 4 + i, 12, a if i % 2 else b)
        im.rect(9, 3, 13, 4, a); im.rect(9, 7, 13, 8, b); im.rect(9, 11, 13, 12, a)
    elif shape == "bottle":
        im.rect(7, 1, 8, 3, (90, 60, 40)); im.rect(6, 4, 9, 5, (200, 230, 200)); im.rect(4, 6, 11, 14, (200, 230, 200))
        im.rect(5, 8, 10, 13, a); im.rect(5, 10, 10, 11, b); im.rect(4, 6, 4, 14, (235, 250, 240))
    elif shape == "meat":
        im.ellipse(8, 9, 6.5, 4.8, a, light=la, dark=da)
        for i in range(18):
            x = 3 + int(im.rnd(i) * 10); y = 6 + int(im.rnd(i + 30) * 6)
            if im.get(x, y)[3]: im.set(x, y, b if i % 2 else shade(a, .8))
    elif shape == "dough":
        im.ellipse(8, 9.5, 6.4, 4.6, a, light=la, dark=da); im.ellipse(6, 7.5, 2, 1.2, mix(a, (255, 255, 255), .6))
    elif shape == "round_flat":
        im.ellipse(8, 8.5, 7.3, 6, a, light=la, dark=b)
    elif shape == "shrimp":
        for i in range(8): im.ellipse(4 + i * 1.1, 8 + (abs(i - 4) * 0.7), 2, 2, a if i % 2 else b)
        im.rect(12, 4, 13, 6, a)
    elif shape == "mussel_raw":
        im.ellipse(8, 8, 6, 4, a, light=(80, 80, 110)); im.ellipse(8, 8.5, 3.6, 2, b)
    elif shape == "rings_raw":
        for cx, cy in ((5, 7), (10, 7), (7.5, 11)):
            im.ellipse(cx, cy, 2.6, 2.6, a, dark=b); im.set(int(cx), int(cy), (0, 0, 0)); im.p[int(cy)][int(cx)] = (0, 0, 0, 0)
    elif shape == "bar":
        im.rect(3, 4, 12, 12, a); im.rect(3, 4, 12, 4, la)
        for x in (6, 9): im.rect(x, 4, x, 12, b)
        im.rect(3, 8, 12, 8, b)
    elif shape == "pancake":
        for k in range(4): im.ellipse(8, 11 - k * 1.6, 6.5, 2.4, a, light=la, dark=da)
        im.ellipse(8, 5.6, 3.4, 1.3, b); im.rect(10, 6, 10, 9, b); im.rect(8, 7, 8, 8, (250, 240, 200))
    elif shape == "fries":
        im.rect(4, 8, 11, 14, b); im.rect(4, 8, 11, 8, shade(b, 1.2))
        for i, x in enumerate(range(4, 12)):
            h = 3 + (i * 5) % 4
            im.rect(x, 8 - h, x, 8, a if i % 2 else shade(a, .85))
    elif shape == "v_tava":
        im.ellipse(6.5, 9, 6, 4.6, (60, 60, 66), dark=(40, 40, 46)); im.ellipse(6.5, 8.6, 4.8, 3.4, (90, 90, 98))
        im.rect(12, 7, 15, 8, (40, 30, 26))
    elif shape == "v_tencere":
        im.rect(2, 6, 13, 13, (180, 184, 192)); im.rect(2, 6, 13, 6, (220, 224, 230)); im.rect(2, 13, 13, 13, (130, 134, 142))
        im.ellipse(8, 5, 6.5, 1.8, (200, 204, 212)); im.rect(7, 2, 8, 3, (40, 40, 46)); im.rect(0, 8, 1, 9, (40, 40, 46)); im.rect(14, 8, 15, 9, (40, 40, 46))
    elif shape == "v_tepsi":
        im.rect(1, 6, 14, 11, (120, 124, 132)); im.rect(2, 7, 13, 10, (160, 164, 172)); im.rect(1, 6, 14, 6, (200, 204, 210))
    elif shape == "v_tahta":
        im.rect(2, 4, 12, 12, (176, 126, 70)); im.rect(2, 4, 12, 4, (206, 156, 96)); im.rect(13, 7, 15, 9, (176, 126, 70))
        for y in (6, 9, 11): im.rect(3, y, 11, y, (156, 106, 56))
    elif shape == "v_cezve":
        im.rect(4, 6, 10, 13, (200, 140, 60)); im.rect(3, 5, 11, 5, (230, 170, 80)); im.rect(10, 9, 15, 10, (60, 40, 30))
        im.rect(4, 13, 10, 13, (150, 100, 40))
    else:
        return tf.draw(shape, a, b, seed)
    im.outline()
    return im.p

def rebuild_pack():
    pack = os.path.join(ROOT, "build", "astro_food_pack.zip")
    old = {}
    with zipfile.ZipFile(pack) as z:
        for n in z.namelist(): old[n] = z.read(n)
    add_cases = {}
    def tex(key, px):
        old[f"assets/astro/textures/item/food/{key}.png"] = tf.png(None, px)
        old[f"assets/astro/models/item/food/{key}.json"] = json.dumps(
            {"parent": "minecraft:item/generated", "textures": {"layer0": f"astro:item/food/{key}"}}).encode()
    for i, (k, (n, shape, a, b)) in enumerate(ING.items()):
        tex(f"ing_{k}", draw_extra(shape, rgb(a), rgb(b), 2000 + i)); add_cases.setdefault("paper", []).append(f"ing_{k}")
    for i, v in enumerate(VESSELS):
        tex(f"v_{v}", draw_extra(f"v_{v}", (0, 0, 0), (0, 0, 0), 3000 + i)); add_cases.setdefault("bowl", []).append(f"v_{v}")
    for i, (n, c, a, b, shape) in enumerate(WORLD):
        sid = tf.slug(n)
        if f"assets/astro/textures/item/food/{sid}.png" in old: continue
        tex(sid, draw_extra(shape, rgb(a), rgb(b), 4000 + i)); add_cases.setdefault(CATS[c][1], []).append(sid)
    for base, keys in add_cases.items():
        path = f"assets/minecraft/items/{base}.json"
        if path in old:
            j = json.loads(old[path])
        else:
            j = {"model": {"type": "minecraft:select", "property": "minecraft:custom_model_data", "index": 0, "cases": [],
                           "fallback": {"type": "minecraft:model", "model": f"minecraft:item/{base}"}}}
        j["model"]["cases"] += [{"when": k, "model": {"type": "minecraft:model", "model": f"astro:item/food/{k}"}} for k in keys]
        old[path] = json.dumps(j).encode()
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in old.items(): z.writestr(n, d)
    run = os.environ.get("GITHUB_RUN_NUMBER", "dev")
    repo = os.environ.get("GITHUB_REPOSITORY", "ulucyamanavciyaman-byte/astro-staff")
    sha1 = hashlib.sha1(open(pack, "rb").read()).hexdigest()
    open(os.path.join(ROOT, "src", "main", "resources", "astro_pack.txt"), "w").write(
        f"https://github.com/{repo}/releases/download/build-{run}/astro_food_pack.zip {sha1}\n")

# ============================================================================ the kitchen build
B, ENT = {}, []
def put(x, y, z, s): B[(x, y, z)] = s
def fill(x0, y0, z0, x1, y1, z1, s):
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1): B[(x, y, z)] = s

def kitchen():
    W0, W1, D0, D1, H = -9, 9, 0, 14, 6
    # floor (checker tiles) + front porch
    for x in range(W0 - 1, W1 + 2):
        for z in range(D0 - 3, D1 + 2): put(x, 0, z, "minecraft:polished_andesite")
    for x in range(W0 + 1, W1):
        for z in range(D0 + 1, D1): put(x, 0, z, "minecraft:white_concrete" if (x + z) % 2 else "minecraft:black_concrete")
    # walls
    for y in range(1, H + 1):
        s = "minecraft:white_terracotta" if y < H else "minecraft:smooth_quartz"
        for x in range(W0, W1 + 1): put(x, y, D0, s); put(x, y, D1, s)
        for z in range(D0, D1 + 1): put(W0, y, z, s); put(W1, y, z, s)
    for x in range(W0, W1 + 1): put(x, 1, D0, "minecraft:light_gray_terracotta"); put(x, 1, D1, "minecraft:light_gray_terracotta")
    for z in range(D0, D1 + 1): put(W0, 1, z, "minecraft:light_gray_terracotta"); put(W1, 1, z, "minecraft:light_gray_terracotta")
    fill(-1, 1, D0, 1, 3, D0, "minecraft:air")
    put(-1, 4, D0, "minecraft:spruce_planks"); put(0, 4, D0, "minecraft:spruce_planks"); put(1, 4, D0, "minecraft:spruce_planks")
    for cx in (-6, 5):
        fill(cx, 2, D0, cx + 1, 4, D0, "minecraft:glass_pane")
    for cz in (4, 10):
        fill(W0, 2, cz, W0, 4, cz + 1, "minecraft:glass_pane"); fill(W1, 2, cz, W1, 4, cz + 1, "minecraft:glass_pane")
    # ceiling + recessed lights
    fill(W0, H + 1, D0, W1, H + 1, D1, "minecraft:smooth_quartz")
    for x in (-5, 0, 5):
        for z in (4, 9): put(x, H + 1, z, "minecraft:sea_lantern")
    # roof trim
    for x in range(W0, W1 + 1): put(x, H + 2, D0, "minecraft:spruce_slab"); put(x, H + 2, D1, "minecraft:spruce_slab")
    for z in range(D0, D1 + 1): put(W0, H + 2, z, "minecraft:spruce_slab"); put(W1, H + 2, z, "minecraft:spruce_slab")

    # ---------------- back wall: stove line (z = 13)
    BZ = 13
    # base cabinets with countertop
    for x in range(-8, 9): put(x, 1, BZ, "minecraft:spruce_planks"); put(x, 2, BZ, "minecraft:smooth_stone_slab[type=bottom]")
    # 4 OCAK (stoves) + oven under + hood
    for x in (-3, -1, 1, 3):
        put(x, 1, BZ, "minecraft:blast_furnace[facing={F:front}]"); put(x, 2, BZ, "OCAK")
        ENT.append(("vessel", x, 3.0, BZ, ["tava", "tencere", "tava", "cezve"][(x + 3) // 2]))
    fill(-4, 5, BZ, 4, 5, BZ, "minecraft:polished_deepslate"); fill(-3, 4, BZ, 3, 4, BZ, "minecraft:iron_trapdoor[half=top,facing={F:front},open=false]")
    fill(0, 6, BZ, 0, 6, BZ, "minecraft:iron_bars")
    # backsplash tiles
    for x in range(-8, 9):
        if x in range(-4, 5): continue
        put(x, 3, D1, "minecraft:cyan_glazed_terracotta" if x % 2 else "minecraft:white_glazed_terracotta")
    # SINK (left of stove) + faucet
    put(-6, 2, BZ, "minecraft:water_cauldron[level=3]"); put(-6, 3, D1 - 1, "minecraft:tripwire_hook[facing={F:front}]")
    put(-6, 1, BZ, "minecraft:spruce_trapdoor[facing={F:front},half=bottom,open=true]")
    # DISHWASHER (iron trapdoor front)
    put(-7, 1, BZ, "minecraft:iron_block"); put(-7, 1, BZ - 1, "minecraft:iron_trapdoor[facing={F:back},open=true]")
    # drying rack with plates
    ENT.append(("deco", -7, 2.2, BZ, "tabak")); ENT.append(("deco", -8, 2.2, BZ, "tabak"))
    # cutting boards on the counter (right of stove)
    ENT.append(("vessel", 6, 2.5, BZ, "tahta")); ENT.append(("vessel", 7, 2.5, BZ, "tahta"))
    ENT.append(("vessel", 5, 2.5, BZ, "tepsi"))
    # knife block + utensil jar + spice rack + kettle (çaydanlık) + toaster + microwave
    put(8, 3, BZ, "minecraft:spruce_slab[type=bottom]"); ENT.append(("deco", 8, 3.3, BZ, "bicak_up"))
    put(-8, 3, BZ, "minecraft:decorated_pot[facing={F:front}]")
    for x in range(-8, -4): put(x, 4, D1 - 1, "minecraft:spruce_slab[type=top]")
    for i, k in enumerate(("pul_biber", "karabiber", "kimyon", "tuz")): ENT.append(("deco", -8 + i, 4.6, BZ, "ing_" + k))
    put(6, 4, D1 - 1, "minecraft:spruce_slab[type=top]"); put(7, 4, D1 - 1, "minecraft:spruce_slab[type=top]")
    ENT.append(("deco", 6, 4.62, BZ, "v_cezve")); ENT.append(("deco", 7, 4.62, BZ, "turk_cayi"))
    # upper cabinets
    for x in list(range(-8, -4)) + list(range(5, 9)):
        put(x, 5, D1 - 1, "minecraft:spruce_trapdoor[facing={F:front},half=top,open=true]"); put(x, 5, D1, "minecraft:spruce_planks")
    # hanging pans on the side
    for x in (-4, 4):
        put(x, 4, D1 - 1, "minecraft:tripwire_hook[facing={F:front}]")
    ENT.append(("hang", -4, 3.4, BZ, "v_tava")); ENT.append(("hang", 4, 3.4, BZ, "v_tencere"))

    # ---------------- left wall: FRIDGE + pantry + microwave
    LX = -8
    for z in (9, 10):  # double-door fridge (iron) with chests inside the wall look
        fill(LX, 1, z, LX, 4, z, "minecraft:iron_block")
        put(LX + 1, 2, z, f"minecraft:iron_door[facing={{F:right}},half=lower,hinge={'left' if z == 9 else 'right'}]")
        put(LX + 1, 3, z, f"minecraft:iron_door[facing={{F:right}},half=upper,hinge={'left' if z == 9 else 'right'}]")
        put(LX + 1, 1, z, "CHEST_FRIDGE" + str(z))
    put(LX, 5, 9, "minecraft:white_concrete"); put(LX, 5, 10, "minecraft:white_concrete")
    # pantry shelves (barrels) and microwave
    for z in (6, 7):
        put(LX, 1, z, "minecraft:barrel[facing={F:right}]"); put(LX, 2, z, "minecraft:barrel[facing={F:right}]")
        put(LX, 3, z, "minecraft:spruce_planks")
    put(LX, 4, 6, "minecraft:dropper[facing={F:right}]"); put(LX, 4, 7, "minecraft:smooth_stone")  # microwave + toaster block
    ENT.append(("deco", LX + 0.6, 4.2, 7, "tost_ekmegi"))
    put(LX, 1, 5, "CHEST_PANTRY")
    # trash bin + mop corner
    put(LX, 1, 2, "minecraft:composter"); put(LX, 1, 1, "minecraft:cauldron")

    # ---------------- right wall: equipment chest, coffee corner, plants
    RX = 8
    put(RX, 1, 10, "CHEST_TOOLS"); put(RX, 1, 9, "CHEST_PLATES")
    put(RX, 1, 7, "minecraft:spruce_planks"); put(RX, 2, 7, "minecraft:smooth_stone_slab"); put(RX, 3, 7, "COFFEE")
    put(RX, 1, 6, "minecraft:spruce_planks"); put(RX, 2, 6, "minecraft:smooth_stone_slab")
    ENT.append(("deco", RX, 2.5, 6, "turk_kahvesi_fincani"))
    put(RX, 1, 3, "minecraft:potted_azalea_bush"); put(RX, 1, 2, "minecraft:potted_fern")
    put(RX, 1, 1, "minecraft:potted_red_tulip")

    # ---------------- island with bar stools (center)
    for x in range(-3, 4):
        put(x, 1, 8, "minecraft:spruce_planks"); put(x, 2, 8, "minecraft:polished_diorite_slab[type=bottom]")
    for x in (-3, -1, 1, 3):
        put(x, 1, 6, "minecraft:spruce_fence"); put(x, 2, 6, "minecraft:red_carpet")   # bar stools
    ENT.append(("vessel", -2, 2.5, 8, "tahta")); ENT.append(("vessel", 2, 2.5, 8, "tahta"))
    ENT.append(("deco", 0, 2.55, 8, "fruit"))      # fruit bowl
    put(0, 6, 8, "minecraft:iron_chain"); put(0, 5, 8, "minecraft:lantern[hanging=true]")

    # ---------------- dining table near the door
    for x in (-6, -5):
        put(x, 1, 3, "minecraft:spruce_fence"); put(x, 2, 3, "minecraft:white_carpet")
    put(-7, 1, 3, "minecraft:spruce_stairs[facing={F:left}]"); put(-4, 1, 3, "minecraft:spruce_stairs[facing={F:right}]")
    ENT.append(("deco", -6, 2.1, 3, "tabak")); ENT.append(("deco", -5, 2.1, 3, "tabak"))
    put(5, 1, 2, "minecraft:spruce_fence"); put(5, 2, 2, "minecraft:white_carpet")
    # rug + doormat
    for x in (-1, 0, 1):
        for z in (1, 2): put(x, 1, z, "minecraft:brown_carpet")
    # porch: lantern posts + sign
    for x in (-3, 3):
        fill(x, 1, -2, x, 2, -2, "minecraft:spruce_fence"); put(x, 3, -2, "minecraft:lantern")
    ENT.append(("sign", 0, 5.4, -1, None))
    # shopkeeper (sells all ingredients and kitchen tools)
    ENT.append(("manav", 6, 1, 4, None))

def kitchen_chests():
    keys = list(ING.keys())
    def chest(items):
        return "{Items:[" + ",".join(f"{{Slot:{i}b,{it[1:]}" for i, it in enumerate(items)) + "]}"
    fridge1 = [ing_nbt(k, 32) for k in keys[:27]]
    fridge2 = [ing_nbt(k, 32) for k in keys[27:54]]
    van = ['{id:"minecraft:egg",count:16}', '{id:"minecraft:milk_bucket",count:1}', '{id:"minecraft:milk_bucket",count:1}',
           '{id:"minecraft:milk_bucket",count:1}', '{id:"minecraft:water_bucket",count:1}', '{id:"minecraft:water_bucket",count:1}',
           '{id:"minecraft:sugar",count:64}', '{id:"minecraft:honey_bottle",count:16}', '{id:"minecraft:bread",count:32}',
           '{id:"minecraft:beef",count:32}', '{id:"minecraft:chicken",count:32}', '{id:"minecraft:mutton",count:32}',
           '{id:"minecraft:cod",count:32}', '{id:"minecraft:salmon",count:32}', '{id:"minecraft:potato",count:64}',
           '{id:"minecraft:carrot",count:64}', '{id:"minecraft:apple",count:32}', '{id:"minecraft:cocoa_beans",count:32}',
           '{id:"minecraft:wheat",count:64}', '{id:"minecraft:brown_mushroom",count:32}', '{id:"minecraft:sweet_berries",count:64}',
           '{id:"minecraft:pumpkin",count:16}', '{id:"minecraft:melon_slice",count:32}', '{id:"minecraft:beetroot",count:32}',
           '{id:"minecraft:kelp",count:32}']
    pantry = [ing_nbt(k, 32) for k in keys[54:]] + van
    pantry = pantry[:27]
    rest_van = van[27 - len([ing_nbt(k, 32) for k in keys[54:]]):]
    tools = [vessel_nbt(v, 4) for v in VESSELS] + [OCAK_NBT.replace("count:1", "count:4")]
    for k in ("kasik", "catal", "bicak"):
        tools.append(tf.tool_snbt(k, 8))
    plates = [tf.tool_snbt("tabak", 64), tf.tool_snbt("tabak", 64)] + rest_van
    return {"CHEST_FRIDGE9": chest(fridge1), "CHEST_FRIDGE10": chest(fridge2), "CHEST_PANTRY": chest(pantry),
            "CHEST_TOOLS": chest(tools), "CHEST_PLATES": chest(plates[:27])}

DIRS = {"south": ((0, 1), (-1, 0), 180.0), "north": ((0, -1), (1, 0), 0.0), "east": ((1, 0), (0, 1), 90.0), "west": ((-1, 0), (0, -1), -90.0)}
NAME = {(0, 1): "south", (0, -1): "north", (1, 0): "east", (-1, 0): "west"}
FLAT = "left_rotation:[-0.7071f,0f,0f,0.7071f],right_rotation:[0f,0f,0f,1f]"
UPR = "left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]"

def item_nbt_for(key):
    if key.startswith("ing_"): return ing_nbt(key[4:], 1)
    if key.startswith("v_"): return vessel_nbt(key[2:])
    if key == "tabak": return tf.tool_snbt("tabak", 1)
    if key == "bicak_up": return tf.tool_snbt("bicak", 1)
    if key == "fruit": return '{id:"minecraft:apple",count:1}'
    for row in list(tf.F) + [(w[0], w[1]) for w in WORLD]:
        if tf.slug(row[0]) == key:
            return tf.item_snbt(row[0], row[1], key).replace("count:16", "count:1") if row[1] in tf.CATS else '{id:"minecraft:bread",count:1}'
    return '{id:"minecraft:bread",count:1}'

def emit(d, chests):
    f, r, yaw = DIRS[d]
    def w(x, z): return (r[0] * x + f[0] * z, r[1] * x + f[1] * z)
    def face(nm):
        v = {"back": f, "front": (-f[0], -f[1]), "right": r, "left": (-r[0], -r[1])}[nm]
        return NAME[v]
    def state(s):
        for k in ("front", "back", "left", "right"): s = s.replace("{F:%s}" % k, face(k))
        return s
    def tl(v): return "~" if v == 0 else f"~{v}"
    def pos(x, y, z):
        wx, wz = w(x, z); return f"{tl(wx)} {tl(y)} {tl(wz)}"
    def fpos(x, y, z):
        wx, wz = w(x, z); return f"~{wx + .5:.2f} ~{y:.2f} ~{wz + .5:.2f}"
    L = ["# generated by tools/turk_kitchen.py",
         "kill @e[type=!player,tag=astro_kit,distance=..30]",
         f"fill {pos(-10,1,-3)} {pos(10,10,6)} minecraft:air", f"fill {pos(-10,1,7)} {pos(10,10,15)} minecraft:air"]
    for (x, y, z), s in sorted(B.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2])):
        if s == "minecraft:air": continue
        if s == "OCAK":
            L.append(f'setblock {pos(x,y,z)} minecraft:smoker[facing={face("front")}]{{CustomName:{{text:"Ocak",color:"gold",bold:true}}}}')
        elif s == "COFFEE":
            L.append(f'setblock {pos(x,y,z)} minecraft:brewing_stand{{CustomName:{{text:"Kahve Makinesi",color:"gold",bold:true}}}}')
        elif s.startswith("CHEST_"):
            title = {"CHEST_FRIDGE9": "Buzdolabı 1", "CHEST_FRIDGE10": "Buzdolabı 2", "CHEST_PANTRY": "Kiler",
                     "CHEST_TOOLS": "Mutfak Eşyaları", "CHEST_PLATES": "Tabaklar & Erzak"}[s]
            body = chests[s][:-1] + f',CustomName:{{text:"{title}",color:"gold",bold:true}}}}'
            L.append(f"setblock {pos(x,y,z)} minecraft:chest[facing={face('left') if x > 0 else face('right')}]{body}")
        else:
            L.append(f"setblock {pos(x,y,z)} {state(s)}")
    for kind, x, y, z, data in ENT:
        p = fpos(x, y, z)
        if kind == "vessel":
            L.append(f'summon minecraft:item_display {p} {{Tags:["astro_kit","astro_v_vessel"],item:{vessel_nbt(data)},billboard:"fixed",'
                     f'transformation:{{{FLAT},translation:[0f,0.02f,0f],scale:[0.75f,0.75f,0.75f]}}}}')
            L.append(f'summon minecraft:interaction {p} {{Tags:["astro_kit"],width:0.7f,height:0.3f,response:1b,CustomName:"astro:v:{data}:i:"}}')
        elif kind in ("deco", "hang"):
            rot, bb, sc = (FLAT, '"fixed"', "0.5f") if kind == "deco" else (UPR, '"vertical"', "0.6f")
            if data in ("bicak_up", "v_cezve", "turk_cayi", "turk_kahvesi_fincani", "tost_ekmegi") or data.startswith("ing_"):
                rot, bb, sc = UPR, '"vertical"', "0.4f"
            L.append(f'summon minecraft:item_display {p} {{Tags:["astro_kit"],item:{item_nbt_for(data)},billboard:{bb},'
                     f'transformation:{{{rot},translation:[0f,0f,0f],scale:[{sc},{sc},{sc}]}}}}')
        elif kind == "sign":
            L.append(f'summon minecraft:text_display {p} {{Tags:["astro_kit"],billboard:"vertical",background:0,shadow:1b,'
                     f'transformation:{{{UPR},translation:[0f,0f,0f],scale:[2.6f,2.6f,2.6f]}},text:{{text:"🍳 ASTRO MUTFAK 🍳",color:"gold",bold:true}}}}')
            wx, wz = w(x, z)
            L.append(f'summon minecraft:text_display ~{wx + .5:.2f} ~{y - 0.8:.2f} ~{wz + .5:.2f} {{Tags:["astro_kit"],billboard:"vertical",background:0,'
                     f'transformation:{{{UPR},translation:[0f,0f,0f],scale:[1.1f,1.1f,1.1f]}},text:{{text:"Tava/tencereyi Ocak üstüne koy • Malzemeyi ekle • Boş elle sağ tık = PİŞİR • /tarif",color:"yellow"}}}}')
        elif kind == "manav":
            trades = []
            for k in ING:
                trades.append(f'{{buy:{{id:"minecraft:emerald",count:1}},sell:{ing_nbt(k, 8)},maxUses:2147483647,rewardExp:0b,xp:0,priceMultiplier:0f}}')
            for v in VESSELS:
                trades.insert(0, f'{{buy:{{id:"minecraft:emerald",count:2}},sell:{vessel_nbt(v)},maxUses:2147483647,rewardExp:0b,xp:0,priceMultiplier:0f}}')
            trades.insert(0, f'{{buy:{{id:"minecraft:emerald",count:4}},sell:{OCAK_NBT},maxUses:2147483647,rewardExp:0b,xp:0,priceMultiplier:0f}}')
            L.append(f'summon minecraft:villager {p.replace("~1.00", "~1")} {{Tags:["astro_kit"],NoAI:1b,Invulnerable:1b,Silent:1b,PersistenceRequired:1b,'
                     f'CustomNameVisible:1b,CustomName:{{text:"Manav & Bakkal Ali",color:"gold",bold:true}},Rotation:[{yaw}f,0f],'
                     f'VillagerData:{{profession:"minecraft:farmer",level:5,type:"minecraft:plains"}},Offers:{{Recipes:[{",".join(trades)}]}}}}')
    L += ["particle minecraft:happy_villager ~ ~3 ~ 6 2 6 0 150 force", "playsound minecraft:ui.toast.challenge_complete master @a ~ ~ ~ 2 1"]
    C = ["# generated by tools/turk_kitchen.py",
         "kill @e[type=!player,tag=astro_kit,distance=..30]", "kill @e[type=!player,tag=astro_pl,distance=..20]",
         f"fill {pos(-10,1,-3)} {pos(10,10,6)} minecraft:air", f"fill {pos(-10,1,7)} {pos(10,10,15)} minecraft:air",
         f"fill {pos(-10,0,-3)} {pos(10,0,15)} minecraft:grass_block",
         "playsound minecraft:entity.generic.explode master @a ~ ~ ~ 2 0.8"]
    return L, C

def main():
    recipes, foods = build_recipes()
    res = os.path.join(ROOT, "src", "main", "resources")
    with open(os.path.join(res, "astro_recipes.txt"), "w", encoding="utf-8") as fh:
        for v, keys, sec, name, human, give in recipes:
            fh.write(f"{v}|{keys}|{sec}|{name}|{human}|{give}\n")
    rebuild_pack()
    kitchen()
    chests = kitchen_chests()
    out = os.path.join(res, "data", "astro_staff", "function", "turk")
    os.makedirs(out, exist_ok=True)
    for d in DIRS:
        L, C = emit(d, chests)
        open(os.path.join(out, f"kitchen_build_{d}.mcfunction"), "w", encoding="utf-8").write("\n".join(L) + "\n")
        open(os.path.join(out, f"kitchen_clear_{d}.mcfunction"), "w", encoding="utf-8").write("\n".join(C) + "\n")
    print(f"kitchen: {len(recipes)} recipes, {len(ING)} ingredients, {len(B)} blocks, {len(ENT)} entities")

if __name__ == "__main__":
    main()
