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
import kitchen_models as km

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
    "kahve": ("Türk Kahvesi (Öğütülmüş)", "sack", "4a2a1a", "2a1a10"), "hamur": ("Hamur", "dough", "f2e2c0", "e0c898"),
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
    "yogurt_mayasi": ("Yoğurt Mayası", "cup", "f4f0e0", "c8b890"), "suzme": ("Süzme Yoğurt", "cup", "fbfaf4", "e0dcc8"),
    "susam": ("Susam", "grain", "f0e0b0", "d8c088"), "kahve_cig": ("Çiğ Kahve Çekirdeği", "grain", "8a9a5a", "6a7a3a"),
    "kahve_kavrulmus": ("Kavrulmuş Kahve Çekirdeği", "grain", "3a2414", "5a3a1a"), "sumak": ("Sumak", "jar", "8a1a2a", "f0e0c0"),
    "isot": ("İsot", "jar", "4a1410", "f0e0c0"), "dereotu": ("Dereotu", "leaf", "5a9a3a", "8ac05a"),
    "kabartma_tozu": ("Kabartma Tozu", "sack", "fafaf6", "c8d8e8"), "tarcin": ("Tarçın", "jar", "8a4a1a", "f0e0c0"),
    "kestane": ("Kestane", "veg_round", "6a3a1a", "3a2010"), "sirke": ("Üzüm Sirkesi", "bottle", "c8402a", "8a2a1a"),
    "salep": ("Salep Tozu", "sack", "f4ece0", "d8c8a8"), "tel_kadayif": ("Tel Kadayıf", "pasta", "f2e0a0", "e0c880"),
    "taze_fasulye": ("Taze Fasulye", "veg_long", "5a9a3a", "3a7a2a"), "ihlamur": ("Ihlamur", "leaf", "b8b86a", "8a8a4a"),
    "adacayi": ("Adaçayı", "leaf", "8aa08a", "6a806a"), "kusburnu": ("Kuşburnu", "veg_round", "d8401a", "6a3a1a"),
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
    "cezve": ("Cezve", "Türk kahvesi / sahlep / sıcak çikolata", 6, True),
    "kase": ("Karıştırma Kabı", "Çırpma / karıştırma / ayran / salata (ateş gerekmez)", 4, False),
    "caydanlik": ("Çaydanlık", "Çay / bitki çayı demleme", 12, True),
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
    if re.search(r"Kahvesi|Sahlep|Sıcak Çikolata|Kakao", name): return "cezve"
    if cat == "icecek":
        if re.search(r"Çay|Ihlamur|Ada|Kuşburnu|Nane Limon", name): return "caydanlik"
        if re.search(r"Süt$|Boza|Şerbet", name): return "tencere"
        return "kase"
    if cat in ("corba", "ana", "pilav", "dolma"): return "tencere"
    if cat in ("hamur", "ekmek"): return "tepsi"
    if cat == "tatli":
        if re.search(r"Dondurma|Güllaç|Tiramisu", name): return "kase"
        if re.search(r"Lokum|Cezerye|Pişmaniye", name): return "tencere"
        if re.search(r"Sütlaç|Muhallebi|Keşkül|Supangle|Aşure|Zerde|Helva|Höşmerim|Tavuk Göğsü|Kazandibi", name): return "tencere"
        if re.search(r"Lokma|Tulumba|Pişi|Kemalpaşa|Halka|Katmer", name): return "tava"
        return "tepsi"
    if cat == "meze":
        if re.search(r"Közlenmiş|Şakşuka|Mücver|Babagannuş|Patlıcan", name): return "tava"
        if re.search(r"Pilaki|Fava|Enginar|Börülce", name): return "tencere"
        return "kase"
    if cat == "kahv": return "tahta" if re.search(r"Peynir|Zeytin|Tabağı|Lor|Tulum|Pastırma", name) else ("kase" if re.search(r"Kaymak|Pekmez", name) else "tava")
    if cat == "kuru": return "tava" if re.search(r"Kavrulmuş|Kestane|Leblebi|Çekirde|Popcorn|Badem|Fındık|Fıstığı", name) else ("tencere" if re.search(r"Şekeri|Pestil|Sucuk", name) else "tahta")
    if cat == "dunya":
        if re.search(r"Kek|Brownie|Turta|Lazanya|Pizza|Cheesecake|Fırın|Sufle", name): return "tepsi"
        if re.search(r"Püre|Haşlanmış|Puding|Çorba|Makarna", name): return "tencere"
        if re.search(r"Salata|Smoothie|Milkshake|Limonata|Ayran", name): return "kase"
        return "tava"
    if re.search(r"Fırın|Tandır|Testi|Kiremit|Kuyu|Kağıt|Elbasan|Güveç|Pide|Lahmacun", name): return "tepsi"
    return "tava"

T, K, TP, TH, CZ, KS, CD = "tava", "tencere", "tepsi", "tahta", "cezve", "kase", "caydanlik"
def I(*k): return ["ing:" + x if x and not x.startswith("minecraft:") and x != "su" else x for x in k]
EGG, MILK, SUGAR, HONEY, BREAD = "minecraft:egg", "minecraft:milk_bucket", "minecraft:sugar", "minecraft:honey_bottle", "minecraft:bread"
BEEF, CHICKEN, MUTTON, COD, SALMON = "minecraft:beef", "minecraft:chicken", "minecraft:mutton", "minecraft:cod", "minecraft:salmon"
POTATO, CARROT, APPLE, WHEAT, PUMPKIN = "minecraft:potato", "minecraft:carrot", "minecraft:apple", "minecraft:wheat", "minecraft:pumpkin"
HAND = [  # realistic hand-written recipes (vessel, ingredients, result name)
    # --- breakfast
    (T, [HONEY, BREAD], "Pankek"), (T, I(EGG, MILK, "un", "tereyagi"), "Krep"), (T, I(EGG, EGG, "tuz", "tereyagi"), "Omlet"),
    (T, I(EGG, "tereyagi"), "Sahanda Yumurta"), (T, I(EGG, EGG, "peynir", "tereyagi"), "Peynirli Omlet"),
    (T, I(EGG, EGG, "mantar", "tereyagi"), "Mantarlı Omlet"), (T, I(EGG, EGG, "domates", "biber", "zeytinyagi"), "Menemen"),
    (T, I(EGG, EGG, "sucuk_ham"), "Sucuklu Yumurta"), (K, I(EGG, "su"), "Haşlanmış Yumurta"),
    (K, I(EGG, EGG, "yogurt", "sarimsak", "tereyagi", "pul_biber"), "Çılbır"), (T, I("tereyagi", "un", "kasar", "su"), "Mıhlama"),
    (TH, I("peynir", "zeytin", "domates", "salatalik", HONEY, BREAD), "Kahvaltı Tabağı"), (KS, I("kaymak", HONEY), "Bal Kaymak"),
    (KS, I("tahin", "pekmez"), "Tahin Pekmez"), (T, I(BEEF, "tereyagi", "tuz"), "Kavurma"), (TH, I("peynir"), "Beyaz Peynir"),
    (TH, I("kasar"), "Kaşar Peyniri"), (TH, I(BEEF, "kimyon", "sarimsak", "pul_biber"), "Pastırma"), (T, I("sucuk_ham"), "Sucuk"),
    (T, [BREAD], "Kızarmış Ekmek"), (TH, [BREAD, HONEY], "Ballı Ekmek"), (T, [BREAD, EGG, MILK], "Yumurtalı Ekmek"),
    (T, I(BREAD, "kasar", "tereyagi"), "Kaşarlı Tost"), (T, I(BREAD, "kasar", "sucuk_ham", "tereyagi"), "Sucuklu Tost"),
    (T, I("hamur", "zeytinyagi"), "Pişi"), (T, I("yufka", "peynir", "maydanoz", "tereyagi"), "Gözleme"),
    # --- soups
    (K, I("mercimek", "sogan", CARROT, "tereyagi", "su"), "Mercimek Çorbası"),
    (K, I("mercimek", "bulgur", "pirinc", "salca", "nane_kuru", "su"), "Ezogelin Çorbası"),
    (K, I("yogurt", "pirinc", EGG, "un", "nane_kuru", "su"), "Yayla Çorbası"),
    (K, I("yogurt", "un", "domates", "biber", "salca", "su"), "Tarhana Çorbası"),
    (K, I("domates", "un", "tereyagi", MILK, "su"), "Domates Çorbası"),
    (K, I(CHICKEN, "sehriye", CARROT, "limon", "su"), "Tavuk Suyu Çorbası"), (K, I("sehriye", "salca", "tereyagi", "su"), "Şehriye Çorbası"),
    (K, I("mantar", "un", "tereyagi", MILK, "su"), "Mantar Çorbası"), (K, I(MUTTON, "yogurt", EGG, "limon", "un", "su"), "Düğün Çorbası"),
    (K, I(POTATO, CARROT, "kabak", "domates", "sogan", "su"), "Sebze Çorbası"), (K, I(COD, POTATO, CARROT, "limon", "su"), "Balık Çorbası"),
    (K, I(MUTTON, "sarimsak", "sirke", "un", "tereyagi", "su"), "İşkembe Çorbası"),
    # --- kebab / köfte
    (T, I("kiyma", "pul_biber", "isot", "sogan", "tuz"), "Adana Kebap"), (T, I("kiyma", "isot", "sogan", "tuz"), "Urfa Kebap"),
    (T, I(BEEF, BREAD, "salca", "tereyagi", "yogurt"), "İskender Kebap"), (T, I(BEEF, "sogan", "sumak", "yufka"), "Et Döner"),
    (T, I(CHICKEN, "yogurt", "salca", "yufka"), "Tavuk Döner"), (T, I(BEEF, "sogan", "biber", "domates", "zeytinyagi"), "Şiş Kebap"),
    (T, I(CHICKEN, "yogurt", "salca", "sarimsak"), "Tavuk Şiş"), (TP, I("kiyma", "yufka", "sarimsak", "yogurt", "salca"), "Beyti Kebap"),
    (T, I("patlican", "yogurt", "sarimsak", "kiyma", "tereyagi"), "Alinazik Kebabı"),
    (K, I(BEEF, "patlican", MILK, "un", "tereyagi", "kasar"), "Hünkar Beğendi"),
    (K, I(BEEF, "sogan", "salca", CARROT, POTATO, "su"), "Tas Kebabı"), (K, I(MUTTON, "bezelye", CARROT, POTATO, "sogan", "su"), "Orman Kebabı"),
    (TP, I(MUTTON, "tuz", "karabiber", "su"), "Kuzu Tandır"), (TP, I(BEEF, "domates", "biber", "sogan", "sarimsak", "tereyagi"), "Testi Kebabı"),
    (T, I(MUTTON, "nane_kuru", "tuz", "karabiber"), "Pirzola"), (T, I("kiyma", "sogan", BREAD, "tuz"), "İnegöl Köfte"),
    (T, I("kiyma", "sogan", "tuz"), "Izgara Köfte"), (TP, I("kiyma", POTATO, "domates", "biber", "salca"), "İzmir Köfte"),
    (T, I("kiyma", "pirinc", EGG, "un", "sogan"), "Kadınbudu Köfte"), (KS, I("bulgur", "isot", "salca", "sogan", "sarimsak", "maydanoz"), "Çiğ Köfte"),
    (T, I("bulgur", "kiyma", "ceviz_ic", "sogan", "un", "zeytinyagi"), "İçli Köfte"),
    (KS, I("mercimek", "bulgur", "sogan", "salca", "maydanoz", "su"), "Mercimek Köftesi"),
    (K, I("kiyma", "pirinc", POTATO, "salca", "su"), "Sulu Köfte"), (T, I("kiyma", "sarimsak", BREAD, "tuz"), "Akçaabat Köfte"),
    # --- dough / bakery
    (TP, I("hamur", "kiyma", "domates", "biber", "sogan", "maydanoz"), "Lahmacun"),
    (TP, I("hamur", "kiyma", "sogan", "domates", EGG), "Kıymalı Pide"), (TP, I("hamur", "kasar", "tereyagi", EGG), "Kaşarlı Pide"),
    (TP, I("hamur", BEEF, "kasar", EGG, "tereyagi"), "Karadeniz Pidesi"),
    (TP, I("yufka", "peynir", "maydanoz", EGG, "tereyagi", "su"), "Su Böreği"),
    (T, I("yufka", "peynir", "maydanoz", "zeytinyagi"), "Sigara Böreği"), (TP, I("yufka", "ispanak", "peynir", EGG, MILK), "Kol Böreği"),
    (TP, I("un", "yogurt", EGG, "peynir", "maya", "zeytinyagi"), "Poğaça"), (TP, I("un", MILK, "maya", "tereyagi", SUGAR, EGG), "Açma"),
    (K, I("hamur", "kiyma", "sogan", "yogurt", "sarimsak", "su"), "Mantı"), (TP, I("hamur", "pekmez", "susam"), "Simit"),
    (T, I("un", "yogurt", "maya", "tuz", "su"), "Bazlama"), (T, I("un", "su", "tuz"), "Lavaş"), (TP, I("un", "maya", "su", "tuz"), "Köy Ekmeği"),
    (TP, I("hamur", EGG, "susam"), "Ramazan Pidesi"), (TP, I("hamur", "ceviz_ic", "tarcin", SUGAR), "Ay Çöreği"),
    (TP, I("hamur", "tahin", SUGAR), "Tahinli Çörek"), (TP, I("misir", "un", "yogurt", EGG), "Mısır Ekmeği"),
    # --- meze / salads (cold = mixing bowl)
    (KS, I("domates", "salatalik", "biber", "sogan", "maydanoz", "zeytinyagi"), "Çoban Salatası"),
    (KS, I("domates", "ceviz_ic", "sogan", "pekmez", "maydanoz", "zeytinyagi"), "Gavurdağı Salatası"),
    (KS, I("bulgur", "salca", "maydanoz", "nane", "limon", "zeytinyagi"), "Kısır"), (KS, I("suzme", "sarimsak", "nane_kuru", "dereotu"), "Haydari"),
    (KS, I("yogurt", "salatalik", "sarimsak", "dereotu", "su", "zeytinyagi"), "Cacık"),
    (TH, I("domates", "biber", "sogan", "maydanoz", "pul_biber", "nar"), "Acılı Ezme"),
    (KS, I("nohut", "tahin", "limon", "sarimsak", "zeytinyagi"), "Humus"), (T, I("patlican", "tahin", "sarimsak", "limon", "zeytinyagi"), "Babagannuş"),
    (T, I("patlican", "kabak", "domates", "biber", "sarimsak", "zeytinyagi"), "Şakşuka"),
    (KS, I("fasulye", "sogan", "maydanoz", EGG, "sumak", "zeytinyagi"), "Piyaz"), (T, I("patlican", "sarimsak", "limon", "zeytinyagi"), "Patlıcan Salatası"),
    (KS, I("kirmizi_biber", "ceviz_ic", BREAD, "pekmez", "zeytinyagi"), "Muhammara"),
    (KS, I(POTATO, CARROT, "bezelye", EGG, "yogurt"), "Rus Salatası"), (KS, I("salatalik", "biber", "sirke", "tuz", "sarimsak", "su"), "Turşu"),
    (T, I("kabak", EGG, "un", "dereotu", "peynir", "zeytinyagi"), "Mücver"), (KS, I("minecraft:beetroot", "sarimsak", "yogurt", "zeytinyagi"), "Pancar Salatası"),
    (T, I("kirmizi_biber", "sarimsak", "zeytinyagi", "sirke"), "Közlenmiş Biber"),
    # --- dolma
    (K, I("asma_yapragi", "pirinc", "sogan", "nane_kuru", "zeytinyagi", "limon"), "Yaprak Sarma"),
    (K, I("biber", "pirinc", "kiyma", "domates", "salca", "su"), "Biber Dolması"), (K, I("lahana", "pirinc", "kiyma", "salca", "su"), "Lahana Sarması"),
    (K, I("midye", "pirinc", "sogan", "karabiber", "limon"), "Midye Dolma"), (K, I("kabak", "kiyma", "pirinc", "domates", "su"), "Kabak Dolması"),
    # --- mains
    (TP, I("patlican", "kiyma", "sogan", "domates", "biber", "zeytinyagi"), "Karnıyarık"),
    (TP, I("patlican", "sogan", "domates", "sarimsak", "zeytinyagi"), "İmam Bayıldı"),
    (K, I("fasulye", "salca", "sogan", "tereyagi", "su"), "Kuru Fasulye"), (K, I("nohut", BEEF, "salca", "sogan", "su"), "Etli Nohut"),
    (K, I("taze_fasulye", "domates", "sogan", "zeytinyagi", "su"), "Taze Fasulye"), (TP, I("patlican", "kiyma", "domates", "sogan", "biber"), "Musakka"),
    (K, I("patlican", "kabak", POTATO, "biber", "domates", "su"), "Türlü"), (T, I(CHICKEN, "biber", "domates", "sogan", "mantar"), "Tavuk Sote"),
    (T, I(BEEF, "biber", "sogan", "domates"), "Et Sote"), (K, I("bamya", BEEF, "domates", "limon", "su"), "Bamya"),
    (K, I("ispanak", "pirinc", "sogan", "yogurt"), "Ispanak Yemeği"), (K, I("pirasa", CARROT, "pirinc", "limon", "zeytinyagi", "su"), "Zeytinyağlı Pırasa"),
    (K, I("bezelye", CARROT, POTATO, "salca", "su"), "Bezelye Yemeği"), (K, I(CHICKEN, "ceviz_ic", BREAD, "sarimsak", "pul_biber", "su"), "Çerkez Tavuğu"),
    (K, I(WHEAT, MUTTON, "tereyagi", "su", "tuz"), "Keşkek"), (TP, I(CHICKEN, POTATO, "salca", "zeytinyagi"), "Fırın Tavuk"),
    (T, I(CHICKEN, "salca", "pul_biber"), "Tavuk Kanat"), (K, I("lahana", "kiyma", "salca", "pirinc", "su"), "Kapuska"),
    (TP, I(BEEF, "patlican", "domates", "biber", "sogan"), "Güveç"), (K, I(MUTTON, POTATO, CARROT, "sogan", "su"), "Kuzu Haşlama"),
    # --- rice / pasta
    (K, I("pirinc", "tereyagi", "su", "tuz"), "Pirinç Pilavı"), (K, I("bulgur", "salca", "sogan", "tereyagi", "su"), "Bulgur Pilavı"),
    (K, I("pirinc", "sehriye", "tereyagi", "su"), "Şehriyeli Pilav"), (K, I("pirinc", "uzum", "findik_ic", "tarcin", "tereyagi", "su"), "İç Pilav"),
    (K, I("pirinc", "nohut", "tereyagi", "su"), "Nohutlu Pilav"), (K, I("makarna", "su", "tuz", "salca"), "Spagetti"),
    (TP, I("makarna", MILK, EGG, "kasar", "tereyagi"), "Fırın Makarna"), (K, I("makarna", "kiyma", "salca", "su"), "Kıymalı Makarna"),
    (K, I("makarna", "yogurt", "sarimsak", "tereyagi", "pul_biber", "su"), "Yoğurtlu Makarna"), (K, I("hamur", "tereyagi", "su", "tuz"), "Erişte"),
    # --- seafood
    (T, I(COD, "un", "zeytinyagi", "tuz"), "Hamsi Tava"), (T, I(COD, "limon", "zeytinyagi", "tuz"), "Levrek Izgara"),
    (T, I(SALMON, "limon", "tereyagi"), "Somon Izgara"), (T, I("kalamar", "un", "zeytinyagi", "tuz"), "Kalamar Tava"),
    (T, I("midye", "un", "zeytinyagi", "tuz"), "Midye Tava"), (TP, I("karides", "domates", "biber", "kasar", "tereyagi"), "Karides Güveç"),
    (K, I(COD, "domates", "sogan", "limon", "su"), "Hamsi Buğulama"),
    # --- street food
    (T, I(COD, BREAD, "sogan", "marul"), "Balık Ekmek"), (TP, I(POTATO, "tereyagi", "kasar", "misir", "zeytin"), "Kumpir"),
    (T, I(BEEF, "yufka", "domates", "sogan", "maydanoz"), "Tantuni"), (T, I(BREAD, "kiyma", "salca", "sarimsak"), "Islak Hamburger"),
    (T, I(MUTTON, BREAD, "kimyon", "pul_biber"), "Kokoreç"), (K, I("misir", "su", "tuz"), "Haşlanmış Mısır"), (T, I("misir", "tuz"), "Közlenmiş Mısır"),
    (T, I("kestane"), "Kestane Kebap"),
    # --- desserts
    (TP, I("yufka", "fistik", "tereyagi", SUGAR, "su", "limon"), "Baklava"), (TP, I("yufka", "ceviz_ic", "tereyagi", SUGAR, "su"), "Cevizli Baklava"),
    (TP, I("tel_kadayif", "peynir", "tereyagi", SUGAR, "su", "fistik"), "Künefe"), (TP, I("tel_kadayif", "ceviz_ic", "tereyagi", SUGAR, "su"), "Kadayıf"),
    (K, I(MILK, "pirinc", SUGAR, "nisasta"), "Sütlaç"), (TP, I(MILK, "pirinc", SUGAR, "nisasta", "vanilya"), "Fırın Sütlaç"),
    (K, I(MILK, SUGAR, "nisasta", "un", "tereyagi"), "Kazandibi"), (K, I(MILK, SUGAR, "nisasta", "vanilya"), "Muhallebi"),
    (K, I(MILK, SUGAR, "nisasta", "findik_ic"), "Keşkül"), (TP, I("irmik", EGG, "yogurt", SUGAR, "un", "su"), "Revani"),
    (TP, I("irmik", "un", "tereyagi", EGG, SUGAR, "su"), "Şekerpare"), (T, I("un", EGG, "tereyagi", SUGAR, "su", "zeytinyagi"), "Tulumba"),
    (T, I("un", "maya", "su", SUGAR, "zeytinyagi"), "Lokma"), (K, I(WHEAT, "nohut", "fasulye", "kayisi", "incir", SUGAR), "Aşure"),
    (KS, I("yufka", MILK, SUGAR, "gul", "nar", "ceviz_ic"), "Güllaç"), (T, I("irmik", "tereyagi", MILK, SUGAR), "İrmik Helvası"),
    (T, I("un", "tereyagi", SUGAR, MILK), "Un Helvası"), (K, I("tahin", SUGAR, "ceviz_ic"), "Tahin Helvası"),
    (K, I(PUMPKIN, SUGAR, "ceviz_ic", "tahin"), "Kabak Tatlısı"), (TP, I(APPLE, SUGAR, "kaymak", "su"), "Ayva Tatlısı"),
    (K, I(CHICKEN, MILK, SUGAR, "pirinc", "tarcin"), "Tavuk Göğsü"), (TP, I("un", EGG, "tereyagi", "cikolata", MILK), "Profiterol"),
    (K, I(MILK, "kakao_tozu", SUGAR, "nisasta"), "Supangle"), (TP, I("un", EGG, SUGAR, MILK, "krema"), "Trileçe"),
    (TP, I("un", "tereyagi", SUGAR, EGG, "vanilya", "kabartma_tozu"), "Kurabiye"), (TP, I("peynir", "krema", EGG, SUGAR, "un"), "San Sebastian"),
    (KS, I("kahve", "krema", "kakao_tozu", SUGAR, EGG), "Tiramisu"), (KS, I(MILK, SUGAR, "salep", "krema"), "Maraş Dondurması"),
    (KS, I(MILK, SUGAR, "salep", "fistik"), "Fıstıklı Dondurma"), (KS, I(MILK, SUGAR, "salep", "cikolata"), "Çikolatalı Dondurma"),
    (KS, I(MILK, SUGAR, "salep", "kaymak"), "Kaymaklı Dondurma"), (K, I(SUGAR, "nisasta", "su", "gul", "limon"), "Lokum"),
    (K, I("peynir", "irmik", EGG, SUGAR, "su"), "Kemalpaşa Tatlısı"), (T, I("yufka", "fistik", "kaymak", SUGAR, "tereyagi"), "Katmer"),
    # --- drinks
    (KS, I("yogurt", "su", "tuz"), "Ayran"), (KS, I("suzme", "su", "tuz"), "Ev Yapımı Ayran"),
    (CD, I("cay", "su"), "Türk Çayı"), (CD, I("ihlamur", "su"), "Ihlamur"), (CD, I("adacayi", "su"), "Ada Çayı"),
    (CD, I("kusburnu", "su"), "Kuşburnu Çayı"), (CD, I(APPLE, "tarcin", "su"), "Elma Çayı"), (CD, I("nane", "limon", "su"), "Nane Limon"),
    (CZ, I("kahve", "su"), "Türk Kahvesi Fincanı"), (CZ, I("kahve", MILK, "su"), "Dibek Kahvesi"), (CZ, I("fistik", MILK), "Menengiç Kahvesi"),
    (CZ, I(MILK, "salep", SUGAR, "tarcin"), "Sahlep"), (CZ, I("cikolata", MILK), "Sıcak Çikolata"),
    (CZ, I("minecraft:cocoa_beans", MILK, SUGAR), "Sütlü Kakao"), (K, I(WHEAT, SUGAR, "su", "maya"), "Boza"),
    (KS, I("limon", SUGAR, "su"), "Limonata"), (KS, I("limon", SUGAR, "su", "nane"), "Ev Yapımı Limonata"),
    (K, I("minecraft:sweet_berries", SUGAR, "su"), "Vişne Şerbeti"), (K, I("gul", SUGAR, "limon", "su"), "Gül Şerbeti"),
    (KS, I(MILK, "yogurt_mayasi"), "Kefir"), (KS, I(CARROT, "minecraft:beetroot", "bulgur", "tuz", "su"), "Şalgam"),
    (TH, I("portakal", "portakal"), "Portakal Suyu"), (TH, I("nar", "nar"), "Nar Suyu"), (KS, I("kayisi", SUGAR, "su"), "Kayısı Suyu"),
    (K, I(MILK), "Süt"), (KS, I("minecraft:sweet_berries", MILK, SUGAR), "Milkshake"),
    (KS, I("minecraft:sweet_berries", APPLE, "yogurt"), "Smoothie"),
    # --- world
    (T, I(POTATO, "zeytinyagi", "tuz"), "Patates Kızartması"), (K, I(POTATO, MILK, "tereyagi"), "Patates Püresi"),
    (TP, I("un", EGG, SUGAR, MILK, "kabartma_tozu"), "Kek"), (TP, I("un", EGG, SUGAR, "cikolata", "kabartma_tozu"), "Çikolatalı Kek"),
    (TP, I("hamur", "domates", "kasar"), "Pizza"), (T, I(BREAD, "kiyma", "domates", "marul"), "Hamburger"),
    (KS, I(APPLE, "minecraft:sweet_berries", "portakal", HONEY), "Meyve Salatası"),
]
PROCESS = [  # realistic prep: (vessel, ingredients, result ing, count[, seconds])
    (TH, [WHEAT, WHEAT, WHEAT], "un", 3), (TH, [WHEAT, WHEAT], "irmik", 2),
    (KS, I("un", "su", "tuz", "maya"), "hamur", 4), (KS, I("un", "su", "tuz"), "hamur", 2), (KS, I("un", EGG, "su"), "hamur", 3),
    (TH, I("hamur"), "yufka", 2), (TH, [BEEF], "kiyma", 2), (TH, [MUTTON], "kiyma", 2),
    (KS, [MILK], "krema", 2), (KS, I("krema"), "tereyagi", 2), (K, I(MILK, "limon"), "peynir", 2), (K, I("peynir", "su", "tuz"), "kasar", 1),
    (K, I(MILK, "yogurt_mayasi"), "yogurt", 4, 20), (K, I(MILK, "yogurt"), "yogurt", 4, 20), (K, [MILK, MILK], "kaymak", 2, 16),
    (KS, I("yogurt", "yogurt"), "suzme", 1), (K, I(WHEAT, "su"), "bulgur", 3, 14),
    (T, I("kahve_cig"), "kahve_kavrulmus", 1, 8), (TH, I("kahve_kavrulmus"), "kahve", 2),
    (TH, ["minecraft:cocoa_beans", "minecraft:cocoa_beans"], "kakao_tozu", 2), (K, I("kakao_tozu", SUGAR, "tereyagi"), "cikolata", 3),
    (TH, I(BEEF, "kimyon", "pul_biber", "sarimsak"), "sucuk_ham", 3), (K, I("uzum", "uzum", "su"), "pekmez", 2, 16),
    (TH, I("susam", "susam"), "tahin", 1), (K, I("domates", "domates", "domates", "tuz"), "salca", 2, 16),
    (TH, ["minecraft:brown_mushroom"], "mantar", 2), (TH, I("uzum", "su"), "sirke", 1),
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

    def add(vessel, keys, result_name, give, human=None, alt=False, sec=None):
        keys = sorted(keys)
        k = vessel + "|" + ",".join(keys)
        tries = 0
        while k in used and tries < len(EXTRA):
            extra = EXTRA[tries]; tries += 1
            if extra in keys or len(keys) >= 6: continue
            keys = sorted(keys + [extra]); k = vessel + "|" + ",".join(keys)
        if k in used: return False
        used.add(k)
        sec = sec or (VESSELS[vessel][2] + (2 if len(keys) > 3 else 0))
        h = human or " + ".join(ing_name(x) for x in keys)
        out.append((vessel, ",".join(keys), sec, result_name + (" (alternatif)" if alt else ""), h, give))
        return True

    for v, keys, rn in HAND:
        if rn not in by_name: print("!! unknown food in HAND:", rn); continue
        n, c, s = by_name[rn]
        add(v, keys, n, food_give(n, c, s, CATS))
    for pr in PROCESS:
        v, keys, ik, cnt = pr[:4]
        add(v, keys, ING[ik][0] + (f" x{cnt}" if cnt > 1 else ""), ing_give(ik) + (f" {cnt}" if cnt > 1 else ""),
            sec=pr[4] if len(pr) > 4 else None)
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
    km.install(old, add_cases)   # 3D vessels, appliances and the Ocak (smoker) block model
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
        for k in keys:
            when, mdl = (k if isinstance(k, tuple) else (k, f"astro:item/food/{k}"))
            j["model"]["cases"] = [c for c in j["model"]["cases"] if c.get("when") != when]
            j["model"]["cases"].append({"when": when, "model": {"type": "minecraft:model", "model": mdl}})
        old[path] = json.dumps(j).encode()
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in old.items(): z.writestr(n, d)
    run = os.environ.get("GITHUB_RUN_NUMBER", "dev")
    repo = os.environ.get("GITHUB_REPOSITORY", "ulucyamanavciyaman-byte/astro-staff")
    sha1 = hashlib.sha1(open(pack, "rb").read()).hexdigest()
    open(os.path.join(ROOT, "src", "main", "resources", "astro_pack.txt"), "w").write(
        f"https://github.com/{repo}/releases/download/build-{run}/astro_food_pack.zip {sha1}\n")

# ============================================================================ the kitchen build
# local coords: x = right, z = forward (away from the player), y = up. Door at z = 0, back wall at z = 14.
B, ENT, STORE = {}, [], {}
def put(x, y, z, s): B[(x, y, z)] = s
def fill(x0, y0, z0, x1, y1, z1, s):
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1): B[(x, y, z)] = s

def barrel(x, y, z, title, model=None, face="front", my=None):
    """a storage barrel (opens like a cupboard) dressed with a 3D model"""
    put(x, y, z, "BARREL:" + title); STORE.setdefault(title, [])
    if model: ENT.append(("model", x, y if my is None else my, z, model, face))

def kitchen():
    W0, W1, D0, D1, H = -9, 9, 0, 14, 6
    for x in range(W0 - 1, W1 + 2):
        for z in range(D0 - 3, D1 + 2): put(x, 0, z, "minecraft:polished_andesite")
    for x in range(W0 + 1, W1):
        for z in range(D0 + 1, D1): put(x, 0, z, "minecraft:white_concrete" if (x + z) % 2 else "minecraft:light_gray_concrete")
    for y in range(1, H + 1):
        s = "minecraft:white_terracotta" if y < H else "minecraft:smooth_quartz"
        for x in range(W0, W1 + 1): put(x, y, D0, s); put(x, y, D1, s)
        for z in range(D0, D1 + 1): put(W0, y, z, s); put(W1, y, z, s)
    fill(-1, 1, D0, 1, 3, D0, "minecraft:air")
    fill(-1, 4, D0, 1, 4, D0, "minecraft:spruce_planks")
    for cx in (-6, 4):
        fill(cx, 2, D0, cx + 2, 4, D0, "minecraft:glass_pane")
    for cz in (4, 5):
        fill(W0, 2, cz, W0, 4, cz, "minecraft:glass_pane"); fill(W1, 2, cz, W1, 4, cz, "minecraft:glass_pane")
    # tiled backsplash behind the counters
    for x in range(-8, 9):
        for y in (2, 3): put(x, y, D1, "minecraft:quartz_bricks")
    fill(W0, H + 1, D0, W1, H + 1, D1, "minecraft:smooth_quartz")
    for x in (-5, 0, 5):
        for z in (3, 9): put(x, H + 1, z, "minecraft:sea_lantern")
    for x in range(W0, W1 + 1): put(x, H + 2, D0, "minecraft:spruce_slab"); put(x, H + 2, D1, "minecraft:spruce_slab")
    for z in range(D0, D1 + 1): put(W0, H + 2, z, "minecraft:spruce_slab"); put(W1, H + 2, z, "minecraft:spruce_slab")

    BZ = 13   # ---------------- back counter line (everything faces the door)
    barrel(-8, 1, BZ, "Buzdolabı", "k_buzdolabi"); barrel(-8, 2, BZ, "Buzdolabı • Sebzelik")
    barrel(-7, 1, BZ, "Tencere & Tava Dolabı", "k_dolap")
    put(-6, 1, BZ, "minecraft:water_cauldron[level=3]"); ENT.append(("model", -6, 1, BZ, "k_lavabo", "front"))
    barrel(-5, 1, BZ, "Bulaşık Makinesi", "k_bulasik")
    barrel(-4, 1, BZ, "Çatal Bıçak Çekmecesi", "k_cekmece"); ENT.append(("model", -4, 2, BZ, "k_bicaklik", "front"))
    barrel(-3, 1, BZ, "Baharat Dolabı", "k_dolap"); ENT.append(("model", -3, 2, BZ, "k_baharat", "front"))
    for x, v in zip(range(-2, 3), ("tava", "tencere", "caydanlik", "cezve", "tepsi")):   # 5 OCAK
        put(x, 1, BZ, "minecraft:smoker[facing={F:front},lit=false]")
        ENT.append(("vessel", x, 2, BZ, v))
        ENT.append(("model", x, 3.9, BZ, "k_aspirator", "front"))
    for yy in (4.02, 5.02, 6.02): ENT.append(("model", 0, yy, BZ, "k_baca", "front"))
    barrel(3, 1, BZ, "Tabak Çekmecesi", "k_cekmece"); ENT.append(("vessel", 3, 2, BZ, "kase"))
    barrel(4, 1, BZ, "Alt Dolap", "k_dolap"); ENT.append(("vessel", 4, 2, BZ, "tahta"))
    barrel(5, 1, BZ, "Alt Dolap 2", "k_dolap"); ENT.append(("model", 5, 2, BZ, "k_mikrodalga", "front"))
    barrel(6, 1, BZ, "Kahvaltılık Dolabı", "k_dolap"); ENT.append(("model", 6, 2, BZ, "k_tost", "front"))
    barrel(7, 1, BZ, "Kahve Dolabı", "k_dolap"); put(7, 2, BZ, "COFFEE")
    barrel(8, 1, BZ, "Erzak Dolabı", "k_dolap"); ENT.append(("model", 8, 2, BZ, "k_kahve", "front"))
    for x in list(range(-7, -2)) + list(range(3, 9)):            # upper cabinets
        ENT.append(("model", x, 4.0, BZ, "k_ust_dolap", "front"))
    # ---------------- left wall: tall pantry, trash
    barrel(-8, 1, 11, "Kiler", "k_kiler", "right"); barrel(-8, 2, 11, "Kiler • Üst Raf")
    barrel(-8, 1, 10, "Kiler 2", "k_kiler", "right"); barrel(-8, 2, 10, "Kiler 2 • Üst Raf")
    barrel(-8, 1, 9, "Dondurucu", "k_buzdolabi", "right"); barrel(-8, 2, 9, "Dondurucu • Üst")
    put(-8, 1, 2, "minecraft:composter")
    # ---------------- right wall: tools, plates, plants
    barrel(8, 1, 11, "Mutfak Eşyaları", "k_dolap", "left"); barrel(8, 1, 10, "Tabaklar & Çatal Bıçak", "k_dolap", "left")
    ENT.append(("model", 8, 2, 11, "k_meyve", "left"))
    put(8, 1, 3, "minecraft:potted_azalea_bush"); put(8, 1, 2, "minecraft:potted_fern"); put(8, 1, 1, "minecraft:potted_red_tulip")
    # ---------------- island (cabinets face the stove side) + bar stools on the door side
    for x in range(-2, 3): barrel(x, 1, 8, "Ada Dolabı" + (f" {x + 3}" if x else ""), "k_dolap", "back")
    ENT.append(("vessel", -1, 2, 8, "tahta")); ENT.append(("vessel", 1, 2, 8, "kase")); ENT.append(("model", 0, 2, 8, "k_meyve", "back"))
    for x in (-2, 0, 2): ENT.append(("model", x, 1, 6.6, "k_tabure", "back"))
    put(0, 6, 8, "minecraft:iron_chain"); put(0, 5, 8, "minecraft:lantern[hanging=true]")
    # ---------------- dining corner
    for x in (-6, -5):
        put(x, 1, 3, "minecraft:spruce_fence"); put(x, 2, 3, "minecraft:white_carpet")
    put(-7, 1, 3, "minecraft:spruce_stairs[facing={F:left}]"); put(-4, 1, 3, "minecraft:spruce_stairs[facing={F:right}]")
    ENT.append(("deco", -6, 2.07, 3, "tabak")); ENT.append(("deco", -5, 2.07, 3, "tabak"))
    for x in (-1, 0, 1):
        for z in (1, 2): put(x, 1, z, "minecraft:brown_carpet")
    for x in (-3, 3):
        fill(x, 1, -2, x, 2, -2, "minecraft:spruce_fence"); put(x, 3, -2, "minecraft:lantern")
    ENT.append(("sign", 0, 5.4, -1, None))
    ENT.append(("manav", 6, 1, 4, None))

def kitchen_chests():
    G = {
        "Buzdolabı": I("yogurt", "suzme", "yogurt_mayasi", "peynir", "kasar", "tereyagi", "kaymak", "krema", "maya", "hamur", "yufka", "sucuk_ham",
                       "salca", "zeytin") + [EGG] * 1 + [MILK] * 3,
        "Buzdolabı • Sebzelik": I("domates", "sogan", "sarimsak", "limon", "portakal", "nar", "biber", "kirmizi_biber", "patlican", "kabak",
                                  "salatalik", "maydanoz", "nane", "dereotu", "ispanak", "marul", "mantar", "misir", "bezelye", "bamya", "pirasa",
                                  "lahana", "taze_fasulye", "kayisi", "incir", "uzum", "kusburnu"),
        "Dondurucu": I("kiyma", "karides", "midye", "kalamar") + [BEEF, CHICKEN, MUTTON, COD, SALMON],
        "Kiler": I("un", "pirinc", "bulgur", "mercimek", "nohut", "fasulye", "makarna", "sehriye", "irmik", "nisasta", "tel_kadayif",
                   "asma_yapragi", "kestane") + [SUGAR, HONEY, BREAD, POTATO, CARROT, APPLE, WHEAT],
        "Kiler 2": I("kahve", "kahve_cig", "kahve_kavrulmus", "cay", "ihlamur", "adacayi", "gul", "fistik", "ceviz_ic", "findik_ic", "susam",
                     "tahin", "pekmez", "zeytinyagi", "sirke", "cikolata", "kakao_tozu", "salep", "vanilya", "kabartma_tozu")
                   + ["minecraft:cocoa_beans", "minecraft:sweet_berries", "minecraft:beetroot", PUMPKIN],
        "Baharat Dolabı": I("tuz", "pul_biber", "karabiber", "kimyon", "nane_kuru", "sumak", "isot", "tarcin"),
        "Tencere & Tava Dolabı": ["VESSEL:" + v for v in VESSELS] + ["OCAK"],
        "Çatal Bıçak Çekmecesi": ["TOOL:kasik", "TOOL:catal", "TOOL:bicak"],
        "Bulaşık Makinesi": ["TOOL:tabak"] * 2,
        "Tabak Çekmecesi": ["TOOL:tabak"] * 3,
        "Tabaklar & Çatal Bıçak": ["TOOL:tabak", "TOOL:kasik", "TOOL:catal", "TOOL:bicak"],
        "Mutfak Eşyaları": ["VESSEL:" + v for v in VESSELS] + ["OCAK"],
        "Kahvaltılık Dolabı": I("peynir", "kasar", "zeytin", "kaymak", "tereyagi") + [HONEY, BREAD, BREAD, EGG],
        "Erzak Dolabı": ["minecraft:water_bucket"] * 4 + ["minecraft:milk_bucket"] * 2 + ["minecraft:glass_bottle"],
    }
    def item(k):
        if k.startswith("ing:"): return ing_nbt(k[4:], 32)
        if k.startswith("VESSEL:"): return vessel_nbt(k[7:], 2)
        if k == "OCAK": return OCAK_NBT.replace("count:1", "count:4")
        if k.startswith("TOOL:"): return tf.tool_snbt(k[5:], 64 if k.endswith("tabak") else 16)
        n = 1 if k.endswith("_bucket") else (16 if k in (EGG, HONEY) else 64)
        return f'{{id:"{k}",count:{n}}}'
    out = {}
    for title, keys in G.items():
        assert len(keys) <= 27, (title, len(keys))
        out[title] = "{Items:[" + ",".join(f"{{Slot:{i}b,{item(k)[1:]}" for i, k in enumerate(keys)) + "]"
    missing = [k for k in ING if not any(("ing:" + k) in v for v in G.values())]
    if missing: print("ingredients not stored in the kitchen:", missing)
    return out

DIRS = {"south": ((0, 1), (-1, 0), 180.0), "north": ((0, -1), (1, 0), 0.0), "east": ((1, 0), (0, 1), 90.0), "west": ((-1, 0), (0, -1), -90.0)}
NAME = {(0, 1): "south", (0, -1): "north", (1, 0): "east", (-1, 0): "west"}
FLAT = "left_rotation:[-0.7071f,0f,0f,0.7071f],right_rotation:[0f,0f,0f,1f]"
UPR = "left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]"
# vessel display (must match Kitchen.java): model bottom on the surface, heat vessels sit on the pan supports
LIFT = {"tava": .0625, "tencere": .0625, "tepsi": .0625, "cezve": .0625, "caydanlik": .0625, "tahta": .006, "kase": .006}
HIT = {"tencere": .5, "caydanlik": .8, "cezve": .35, "kase": .4}

def yawq(dx, dz):
    """quaternion that turns the model front (-Z) towards (dx, dz)"""
    import math
    th = math.atan2(-dx, -dz)
    return f"[0f,{math.sin(th / 2):.4f}f,0f,{math.cos(th / 2):.4f}f]"

def item_nbt_for(key):
    if key.startswith("ing_"): return ing_nbt(key[4:], 1)
    if key == "tabak": return tf.tool_snbt("tabak", 1)
    for row in list(tf.F) + [(w[0], w[1]) for w in WORLD]:
        if tf.slug(row[0]) == key:
            return tf.item_snbt(row[0], row[1], key).replace("count:16", "count:1") if row[1] in tf.CATS else '{id:"minecraft:bread",count:1}'
    return '{id:"minecraft:bread",count:1}'

def model_item(k): return f'{{id:"minecraft:paper",count:1,components:{{"minecraft:custom_model_data":{{strings:["{k}"]}}}}}}'

def emit(d, chests):
    f, r, yaw = DIRS[d]
    def w(x, z): return (r[0] * x + f[0] * z, r[1] * x + f[1] * z)
    def vec(nm): return {"back": f, "front": (-f[0], -f[1]), "right": r, "left": (-r[0], -r[1])}[nm]
    def face(nm): return NAME[vec(nm)]
    def state(s):
        for k in ("front", "back", "left", "right"): s = s.replace("{F:%s}" % k, face(k))
        return s
    def tl(v): return "~" if v == 0 else f"~{v}"
    def pos(x, y, z):
        wx, wz = w(x, z); return f"{tl(wx)} {tl(y)} {tl(wz)}"
    def fpos(x, y, z):
        wx, wz = w(x, z); return f"~{wx + .5:.3f} ~{y:.3f} ~{wz + .5:.3f}"
    L = ["# generated by tools/turk_kitchen.py",
         "kill @e[type=!player,tag=astro_kit,distance=..30]",
         f"fill {pos(-10,1,-3)} {pos(10,10,6)} minecraft:air", f"fill {pos(-10,1,7)} {pos(10,10,15)} minecraft:air"]
    for (x, y, z), s in sorted(B.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2])):
        if s == "minecraft:air": continue
        if s == "COFFEE":
            L.append(f'setblock {pos(x,y,z)} minecraft:brewing_stand{{CustomName:{{text:"Kahve Makinesi",color:"gold",bold:true}}}}')
        elif s.startswith("BARREL:"):
            title = s[7:]
            body = chests.get(title, "{Items:[]")
            L.append(f'setblock {pos(x,y,z)} minecraft:barrel[facing=up]{body},CustomName:{{text:"{tf.esc(title)}",color:"gold",bold:true}}}}')
        else:
            L.append(f"setblock {pos(x,y,z)} {state(s)}")
    for e in ENT:
        kind, x, y, z, data = e[:5]
        p = fpos(x, y, z)
        if kind == "vessel":
            q = yawq(*vec("front"))
            L.append(f'summon minecraft:item_display {p} {{Tags:["astro_kit","astro_v_vessel"],item:{vessel_nbt(data)},'
                     f'transformation:{{left_rotation:{q},right_rotation:[0f,0f,0f,1f],translation:[0f,{0.5 + LIFT[data]:.4f}f,0f],scale:[1f,1f,1f]}}}}')
            L.append(f'summon minecraft:interaction {p} {{Tags:["astro_kit"],width:0.75f,height:{HIT.get(data, .3)}f,response:1b,CustomName:"astro:v:{data}:i:"}}')
        elif kind == "model":
            q = yawq(*vec(e[5]))
            sc = "1.004f" if data in ("k_buzdolabi", "k_dolap", "k_cekmece", "k_bulasik", "k_kiler") else "1f"
            L.append(f'summon minecraft:item_display {p} {{Tags:["astro_kit"],item:{model_item(data)},'
                     f'transformation:{{left_rotation:{q},right_rotation:[0f,0f,0f,1f],translation:[0f,0.5f,0f],scale:[{sc},{sc},{sc}]}}}}')
        elif kind == "deco":
            L.append(f'summon minecraft:item_display {p} {{Tags:["astro_kit"],item:{item_nbt_for(data)},'
                     f'transformation:{{{FLAT},translation:[0f,0f,0f],scale:[0.5f,0.5f,0.5f]}}}}')
        elif kind == "sign":
            L.append(f'summon minecraft:text_display {p} {{Tags:["astro_kit"],billboard:"vertical",background:0,shadow:1b,'
                     f'transformation:{{{UPR},translation:[0f,0f,0f],scale:[2.6f,2.6f,2.6f]}},text:{{text:"\U0001f373 ASTRO MUTFAK \U0001f373",color:"gold",bold:true}}}}')
            wx, wz = w(x, z)
            L.append(f'summon minecraft:text_display ~{wx + .5:.2f} ~{y - 0.8:.2f} ~{wz + .5:.2f} {{Tags:["astro_kit"],billboard:"vertical",background:0,'
                     f'transformation:{{{UPR},translation:[0f,0f,0f],scale:[1.0f,1.0f,1.0f]}},text:{{text:"Ocak\'ı yak: Shift + boş elle Ocak\'a sağ tık • Malzemeyi kaba at • Boş elle sağ tık = PİŞİR • /tarif",color:"yellow"}}}}')
        elif kind == "manav":
            trades = []
            for k in ING:
                trades.append(f'{{buy:{{id:"minecraft:emerald",count:1}},sell:{ing_nbt(k, 8)},maxUses:2147483647,rewardExp:0b,xp:0,priceMultiplier:0f}}')
            for v in VESSELS:
                trades.insert(0, f'{{buy:{{id:"minecraft:emerald",count:2}},sell:{vessel_nbt(v)},maxUses:2147483647,rewardExp:0b,xp:0,priceMultiplier:0f}}')
            trades.insert(0, f'{{buy:{{id:"minecraft:emerald",count:4}},sell:{OCAK_NBT},maxUses:2147483647,rewardExp:0b,xp:0,priceMultiplier:0f}}')
            L.append(f'summon minecraft:villager {p.replace("~1.000", "~1")} {{Tags:["astro_kit"],NoAI:1b,Invulnerable:1b,Silent:1b,PersistenceRequired:1b,'
                     f'CustomNameVisible:1b,CustomName:{{text:"Manav & Bakkal Ali",color:"gold",bold:true}},Rotation:[{yaw}f,0f],'
                     f'VillagerData:{{profession:"minecraft:farmer",level:5,type:"minecraft:plains"}},Offers:{{Recipes:[{",".join(trades)}]}}}}')
    L += ["particle minecraft:happy_villager ~ ~3 ~ 6 2 6 0 150 force", "playsound minecraft:ui.toast.challenge_complete master @a ~ ~ ~ 2 1"]
    C = ["# generated by tools/turk_kitchen.py",
         "kill @e[type=!player,tag=astro_kit,distance=..30]", "kill @e[type=!player,tag=astro_pl,distance=..20]",
         "kill @e[type=item_display,tag=astro_v_vessel,distance=..30]", "kill @e[type=item_display,tag=astro_v_ing,distance=..30]",
         "kill @e[type=item_display,tag=astro_v_res,distance=..30]", "kill @e[type=item_display,tag=astro_v_fx,distance=..30]",
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
    from collections import Counter
    print(f"kitchen: {len(recipes)} recipes {dict(Counter(r[0] for r in recipes))}, {len(ING)} ingredients, {len(B)} blocks, {len(ENT)} entities")

if __name__ == "__main__":
    main()
