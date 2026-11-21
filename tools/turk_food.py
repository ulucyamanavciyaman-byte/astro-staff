#!/usr/bin/env python3
"""Generates the Astro Turkish food set:
  - build/astro_food_pack.zip  (resource pack with a 16x16 icon for every food)
  - src/main/resources/data/astro_staff/function/turk/spawn.mcfunction  (/turkyemegi chests)
Pure python (no PIL) so it runs on the GitHub Actions runner as-is.
"""
import json, os, re, struct, sys, zlib, zipfile, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ----------------------------------------------------------------------------- food list
# category -> (display name, base vanilla item, nutrition, saturation, default shape, name color, remainder)
CATS = {
    "corba":  ("Çorbalar",            "mushroom_stew",  6, 7.0,  "bowl",     "gold",         "bowl"),
    "kebap":  ("Kebaplar",            "cooked_beef",   10, 14.0, "kebapplate","red",         None),
    "kofte":  ("Köfteler",            "cooked_mutton",  8, 12.0, "balls",    "dark_red",     None),
    "hamur":  ("Pide, Börek & Hamur", "bread",          8, 10.0, "pide",     "yellow",       None),
    "ekmek":  ("Ekmekler",            "bread",          5, 6.0,  "loaf",     "yellow",       None),
    "kahv":   ("Kahvaltılık",         "baked_potato",   5, 6.0,  "plate",    "white",        None),
    "meze":   ("Mezeler & Salatalar", "beetroot",       4, 4.0,  "plate",    "green",        None),
    "dolma":  ("Dolma & Sarma",       "dried_kelp",     6, 7.0,  "rolls",    "dark_green",   None),
    "ana":    ("Ana Yemekler",        "rabbit_stew",    8, 10.0, "pot",      "gold",         "bowl"),
    "pilav":  ("Pilav & Makarna",     "suspicious_stew",7, 8.0,  "rice",     "white",        "bowl"),
    "deniz":  ("Deniz Ürünleri",      "cooked_cod",     8, 10.0, "fish",     "aqua",         None),
    "sokak":  ("Sokak Lezzetleri",    "cooked_porkchop",8, 9.0,  "wrap",     "gold",         None),
    "tatli":  ("Tatlılar",            "pumpkin_pie",    6, 5.0,  "slice",    "light_purple", None),
    "icecek": ("İçecekler",           "honey_bottle",   2, 2.0,  "glass",    "aqua",         "glass_bottle"),
    "kuru":   ("Kuruyemiş & Şekerleme","cookie",        3, 3.0,  "nuts",     "gold",         None),
}

# name, category, main color, accent color, [shape override]
F = [
 # --- çorbalar
 ("Mercimek Çorbası","corba","e8892b","b22a1a"),("Ezogelin Çorbası","corba","d9622b","f2d06b"),
 ("Yayla Çorbası","corba","f2ead2","4f8f3a"),("Tarhana Çorbası","corba","d8552f","f0c060"),
 ("İşkembe Çorbası","corba","efe6d4","b22a1a"),("Kelle Paça Çorbası","corba","f4efe4","c9b28a"),
 ("Domates Çorbası","corba","d23a26","f6f0e0"),("Tavuk Suyu Çorbası","corba","efd36a","f6f0e0"),
 ("Düğün Çorbası","corba","f2e3b8","b22a1a"),("Toyga Çorbası","corba","efe7cc","4f8f3a"),
 ("Mantar Çorbası","corba","c7a983","6b4b2a"),("Şehriye Çorbası","corba","f0b860","f6e7a0"),
 ("Yoğurt Çorbası","corba","f6f2e6","4f8f3a"),("Analı Kızlı Çorbası","corba","c8401f","8a5a2b"),
 ("Lebeniye Çorbası","corba","f3eddc","9a7a50"),("Beyran Çorbası","corba","b8341c","f2e6c8"),
 ("Arabaşı Çorbası","corba","c4381c","f2e0b0"),("Kesme Çorbası","corba","e09a4a","f6ecd0"),
 ("Ekşili Köfte Çorbası","corba","efdca0","7a3a1c"),("Sebze Çorbası","corba","e2953a","4f9a3a"),
 ("Balık Çorbası","corba","efe0b4","e07a50"),("Kuzu Kulağı Çorbası","corba","8aa84a","f2ecd8"),
 # --- kebaplar
 ("Adana Kebap","kebap","9b3a1c","d84a26","skewer"),("Urfa Kebap","kebap","8a4a24","e8c070","skewer"),
 ("İskender Kebap","kebap","8a4a2a","d8402a"),("Et Döner","kebap","8e5530","f0d9a0","doner"),
 ("Tavuk Döner","kebap","d9a35a","f2e2b0","doner"),("Şiş Kebap","kebap","8a4022","4f9a3a","skewer"),
 ("Tavuk Şiş","kebap","e0a050","d84a26","skewer"),("Beyti Kebap","kebap","9b3a1c","f0d090"),
 ("Cağ Kebabı","kebap","8a4a24","5a9a3a","skewer"),("Tandır Kebabı","kebap","7a4024","d8b07a"),
 ("Testi Kebabı","kebap","b55a2a","c46a3a","pot"),("Patlıcan Kebabı","kebap","4a2a5a","9b3a1c","skewer"),
 ("Alinazik Kebabı","kebap","f2ecd8","8a4022"),("Kuzu Tandır","kebap","8a5030","e8d0a0"),
 ("Ciğer Şiş","kebap","5a201a","f2e8c8","skewer"),("Kuşbaşı Kebap","kebap","8a3a20","4f9a3a"),
 ("Orman Kebabı","kebap","8a4a2a","e8a040","pot"),("Hünkar Beğendi","kebap","f0e6cc","8a3a1c"),
 ("Tas Kebabı","kebap","9a3e20","e8b070","pot"),("Çöp Şiş","kebap","8a4022","e8d8a0","skewer"),
 ("Elbasan Tava","kebap","f0d48a","8a4022","pot"),("Kağıt Kebabı","kebap","f4f0e8","9a4020"),
 ("Simit Kebabı","kebap","9b3a1c","e0b070","skewer"),("Kiremitte Kebap","kebap","b8542a","8a3020","pot"),
 ("Kuyu Kebabı","kebap","7a4024","f0d8a0"),("Fırın Kebabı","kebap","8a4a2a","d8a050"),
 ("Yoğurtlu Kebap","kebap","f2ecdc","9b3a1c"),("Halep Kebabı","kebap","9b3a1c","e8c080"),
 ("Kaburga Dolması","kebap","7a3a20","e8d0a0"),("Pirzola","kebap","8a4022","f2e4c4","chop"),
 # --- köfteler
 ("İnegöl Köfte","kofte","7a3e22","e8c070"),("Izgara Köfte","kofte","6e3a20","4f9a3a"),
 ("Akçaabat Köfte","kofte","7e4024","d84a26"),("Tekirdağ Köfte","kofte","74381e","f0e0a0"),
 ("Sulu Köfte","kofte","8a4022","d8502a","bowl"),("İzmir Köfte","kofte","8a4022","d8402a","pot"),
 ("Kadınbudu Köfte","kofte","b8763a","f0d090"),("Çiğ Köfte","kofte","b8341c","4f9a3a"),
 ("İçli Köfte","kofte","b8742e","7a3e22","drops"),("Mercimek Köftesi","kofte","e09a3a","4f9a3a"),
 ("Kuru Köfte","kofte","7a3e22","f0d090"),("Dalyan Köfte","kofte","8a4a2a","f0d040"),
 ("Sultanahmet Köftesi","kofte","74381e","f2ecd0"),("Kasap Köfte","kofte","7a3e22","d84a26"),
 ("Hasanpaşa Köfte","kofte","8a4a2a","f2e4b0"),("Kıymalı Köfte Şiş","kofte","8a3a1e","d8b070","skewer"),
 ("Firik Köftesi","kofte","9a7a3a","4f9a3a"),("Islama Köfte","kofte","74381e","d84a26"),
 # --- pide / börek / hamur
 ("Lahmacun","hamur","e8c080","c4381c","lahmacun"),("Kıymalı Pide","hamur","e0b060","8a3a1c"),
 ("Kaşarlı Pide","hamur","e0b060","f6d84a"),("Kuşbaşılı Pide","hamur","e0b060","7a3a1c"),
 ("Karadeniz Pidesi","hamur","e8b860","f6e06a"),("Etli Ekmek","hamur","e8c080","9b3a1c","lahmacun"),
 ("Gözleme","hamur","eccf8a","4f9a3a","gozleme"),("Su Böreği","hamur","f0d090","f6f0e0","borek"),
 ("Sigara Böreği","hamur","e8b050","f6f2e8","cigars"),("Kol Böreği","hamur","e0a848","f6f0e0","borek"),
 ("Talaş Böreği","hamur","f0c060","8a3a1c","borek"),("Paçanga Böreği","hamur","e8b050","a0402a","cigars"),
 ("Çiğ Börek","hamur","f0c87a","8a3a1c","gozleme"),("Kete","hamur","d8a050","f2e0a0","loaf"),
 ("Poğaça","hamur","e8b050","f2e4b8","bun"),("Açma","hamur","e8b45a","f6e8c0","bun"),
 ("Mantı","hamur","f2e8cc","c4381c","manti"),("Hingel","hamur","f0e2c0","d8502a","manti"),
 ("Pişi","hamur","e8c070","f6e8c0","bun"),("Bükme","hamur","e0a848","f2d8a0","gozleme"),
 ("Kaşarlı Tost","hamur","e8b45a","f6d84a","toast"),("Sucuklu Tost","hamur","e8b45a","9b2a1a","toast"),
 # --- ekmekler
 ("Simit","ekmek","b86a2a","f0e2c0","simit"),("Ramazan Pidesi","ekmek","d89a4a","2a2a2a","pide"),
 ("Bazlama","ekmek","eccc8a","b88a4a","round"),("Yufka","ekmek","f4e8c8","d8c090","round"),
 ("Lavaş","ekmek","f2e2b8","c8a060","round"),("Köy Ekmeği","ekmek","a8682a","e0b878"),
 ("Mısır Ekmeği","ekmek","e8b830","b88a2a"),("Kumru","ekmek","d89a4a","9b2a1a","sandwich"),
 ("Ay Çöreği","ekmek","d8984a","6a4a2a","simit"),("Tahinli Çörek","ekmek","b8783a","6a4a2a","round"),
 ("Kandil Simidi","ekmek","d8984a","f2e0b0","simit"),("Ekmek Kadayıfı","ekmek","b8742a","f6f2e6","round"),
 # --- kahvaltılık
 ("Menemen","kahv","d8402a","f6d84a","pan"),("Sucuklu Yumurta","kahv","f6f2e8","9b2a1a","pan"),
 ("Çılbır","kahv","f6f2e8","d8502a"),("Beyaz Peynir","kahv","f8f6ee","e8e2d0","cheese"),
 ("Kaşar Peyniri","kahv","f6d860","e0b830","cheese"),("Tulum Peyniri","kahv","f4efe0","d8d0b8","cheese"),
 ("Siyah Zeytin","kahv","2a1e2a","5a4a5a","olives"),("Yeşil Zeytin","kahv","6a8a2a","a0b84a","olives"),
 ("Bal Kaymak","kahv","f6f0dc","e8a020"),("Tahin Pekmez","kahv","5a2a1a","d8b880","bowl"),
 ("Mıhlama","kahv","f6d860","f2e8c0","pan"),("Sucuk","kahv","9b2a1a","f2e0c0","sausage"),
 ("Pastırma","kahv","9b3a1c","c86a2a"),("Kavurma","kahv","7a3e22","f2e4c0","pan"),
 ("Haşlanmış Yumurta","kahv","f8f6f0","f6c830","egg"),("Kahvaltı Tabağı","kahv","f6f2e6","d8402a"),
 ("Gözleme Kahvaltı","kahv","eccf8a","4f9a3a","gozleme"),("Lor Peyniri","kahv","fbfaf4","eeeadc","cheese"),
 # --- meze / salata
 ("Çoban Salatası","meze","d8402a","4f9a3a"),("Gavurdağı Salatası","meze","c4381c","6a3a1c"),
 ("Kısır","meze","d89a3a","4f9a3a"),("Haydari","meze","f6f4ea","4f9a3a"),
 ("Cacık","meze","f2f2ea","6aa84a","bowl"),("Acılı Ezme","meze","c4301c","4f9a3a"),
 ("Humus","meze","e8d0a0","d8502a"),("Babagannuş","meze","c8b088","4a2a5a"),
 ("Şakşuka","meze","4a2a5a","d8402a"),("Fava","meze","f0d870","4f9a3a"),
 ("Atom","meze","f2eee0","b8301c"),("Piyaz","meze","f2ead2","b8341c"),
 ("Patlıcan Salatası","meze","a8906a","4f9a3a"),("Muhammara","meze","b8401e","6a3a1c"),
 ("Pancar Salatası","meze","8a1a4a","f2eee0"),("Rus Salatası","meze","f2ecd0","e08a2a"),
 ("Turşu","meze","8aa83a","d8c84a","jar"),("Tarama","meze","f2b8b0","f6f0e8"),
 ("Barbunya Pilaki","meze","c46a5a","e8902a"),("Deniz Börülcesi","meze","4a8a3a","f2f0e0"),
 ("Zeytinyağlı Enginar","meze","b8c870","e8902a"),("Semizotu Salatası","meze","5a9a3a","f6f4ea"),
 ("Közlenmiş Biber","meze","c4301c","6a9a3a"),("Mücver","meze","b8a040","6a9a3a","balls"),
 # --- dolma / sarma
 ("Yaprak Sarma","dolma","4a6a2a","f2e8b8"),("Biber Dolması","dolma","4f9a3a","f2e4b8","stuffed"),
 ("Kabak Dolması","dolma","8ab04a","f2e4b8","stuffed"),("Lahana Sarması","dolma","b8c890","9b3a1c"),
 ("Midye Dolma","dolma","2a2a3a","e8902a","mussel"),("Patlıcan Dolması","dolma","4a2a5a","9b3a1c","stuffed"),
 ("Domates Dolması","dolma","d8302a","f2e4b8","stuffed"),("Kuru Dolma","dolma","9a3a2a","6a3a1c","stuffed"),
 ("Pazı Sarması","dolma","3a6a2a","9b3a1c"),("Zeytinyağlı Sarma","dolma","5a7a2a","f6ecc0"),
 # --- ana yemekler
 ("Karnıyarık","ana","4a2a5a","9b3a1c","stuffed"),("İmam Bayıldı","ana","4a2a5a","d8402a","stuffed"),
 ("Kuru Fasulye","ana","f2e6cc","c8401e"),("Etli Nohut","ana","e8c070","b8401e"),
 ("Taze Fasulye","ana","5a9a3a","d8402a"),("Musakka","ana","4a2a5a","b8401e"),
 ("Türlü","ana","d86a2a","5a9a3a"),("Güveç","ana","b8401e","5a9a3a"),
 ("Kuzu Haşlama","ana","f0e2c0","8a4a2a"),("Tavuk Sote","ana","e8b050","d8402a"),
 ("Et Sote","ana","7a3e22","d8402a"),("Bamya","ana","5a8a2a","c8401e"),
 ("Ispanak Yemeği","ana","3a6a2a","f2f0e0"),("Zeytinyağlı Pırasa","ana","c8d888","e8902a"),
 ("Zeytinyağlı Kereviz","ana","f2ecd0","e8902a"),("Bezelye Yemeği","ana","6ab84a","d8502a"),
 ("Çerkez Tavuğu","ana","e8d8b0","d8502a"),("Keşkek","ana","f0e2c0","d84a26"),
 ("Tirit","ana","e8c888","8a4a2a"),("Mumbar","ana","8a4a2a","d8b070","sausage"),
 ("Kelle","ana","b8a080","5a3a2a"),("Hünkar Kebabı","ana","8a3a1c","f2ecd0"),
 ("Tavuklu Pilav Üstü","ana","f2ecd8","e8b050"),("Saray Köftesi","ana","7a3e22","f2e8c8"),
 ("Etli Kuru Fasulye","ana","f2e2c4","8a3a1c"),("Kapuska","ana","c8d090","c8401e"),
 ("Fırın Tavuk","ana","d88a3a","f2d8a0","drumstick"),("Tavuk Kanat","ana","d8782a","b8401e","drumstick"),
 ("Kuzu İncik","ana","7a3e22","e8d0a0","drumstick"),("Patates Oturtma","ana","e8c070","b8401e"),
 # --- pilav / makarna
 ("Pirinç Pilavı","pilav","f6f4ec","efe8d0"),("Bulgur Pilavı","pilav","c8963a","b8401e"),
 ("İç Pilav","pilav","c89a6a","2a1e1e"),("Perde Pilavı","pilav","d89a40","f2e6c4","dome"),
 ("Nohutlu Pilav","pilav","f6f2e6","e8c070"),("Şehriyeli Pilav","pilav","f6f0e0","c8902a"),
 ("Domatesli Bulgur","pilav","c86a2a","5a9a3a"),("Hamsili Pilav","pilav","5a6a7a","f2e6c4","dome"),
 ("Spagetti","pilav","f2d070","d8402a","noodles"),("Fırın Makarna","pilav","f2c050","d89030","slice"),
 ("Erişte","pilav","f0d080","f6f0d8","noodles"),("Yoğurtlu Makarna","pilav","f6f0e0","d84a26","noodles"),
 ("Kıymalı Makarna","pilav","f0c860","8a3a1c","noodles"),("Bulgurlu Köfte Pilavı","pilav","c8963a","7a3e22"),
 # --- deniz ürünleri
 ("Hamsi Tava","deniz","5a6a7a","e8b050"),("Levrek Izgara","deniz","a8b0b8","e8902a"),
 ("Çipura Izgara","deniz","b8c0c8","d8a050"),("Midye Tava","deniz","e8b050","f2f0e0","mussel"),
 ("Kalamar Tava","deniz","f0d090","f6f2e6","rings"),("Karides Güveç","deniz","e87050","d8402a","pot"),
 ("Lüfer Izgara","deniz","6a7a8a","e8902a"),("Palamut Izgara","deniz","4a5a6a","d8b070"),
 ("Uskumru Izgara","deniz","3a5a5a","e8d090"),("Hamsi Buğulama","deniz","5a6a7a","d8402a"),
 ("Somon Izgara","deniz","f08a5a","f6f0e0"),("Lakerda","deniz","c86a6a","f2f0e8"),
 # --- sokak lezzetleri
 ("Balık Ekmek","sokak","d8a050","6a7a8a","sandwich"),("Kokoreç","sokak","9a5a2a","d8402a","sandwich"),
 ("Tantuni","sokak","f2e2b8","9b3a1c"),("Kumpir","sokak","c8984a","f6d84a","kumpir"),
 ("Islak Hamburger","sokak","c88a4a","8a3a1c","burger"),("Et Dürüm","sokak","f2e2b8","8a4022"),
 ("Tavuk Dürüm","sokak","f2e2b8","e0a050"),("Çiğ Köfte Dürüm","sokak","f2e2b8","b8341c"),
 ("Ciğer Dürüm","sokak","f2e2b8","5a201a"),("Haşlanmış Mısır","sokak","f6d030","6a9a3a","corn"),
 ("Közlenmiş Mısır","sokak","e8b030","5a3a1a","corn"),("Kestane Kebap","sokak","7a4a2a","f2e0b0","nuts"),
 ("Söğüş","sokak","f2e8d0","8a4022"),("Sokak Lahmacunu","sokak","e8c080","c4381c","lahmacun"),
 # --- tatlılar
 ("Baklava","tatli","e8b050","5a9a3a","baklava"),("Fıstıklı Baklava","tatli","e8b050","4f9a3a","baklava"),
 ("Cevizli Baklava","tatli","e8b050","8a5a2a","baklava"),("Künefe","tatli","e88a2a","4f9a3a","round"),
 ("Kadayıf","tatli","e8a840","f2d8a0","nest"),("Burma Kadayıf","tatli","e09a30","4f9a3a","nest"),
 ("Sütlaç","tatli","f6f2e4","b8783a","pudding"),("Fırın Sütlaç","tatli","f2e8d0","a8582a","pudding"),
 ("Kazandibi","tatli","f2e4c4","a8602a"),("Tavuk Göğsü","tatli","f6f4ec","b8783a"),
 ("Revani","tatli","f0c050","f6f0e0"),("Şekerpare","tatli","e8a840","b8783a","bun"),
 ("Tulumba","tatli","e8a030","f6d88a","cigars"),("Lokma","tatli","e8a030","f6e0a0","balls"),
 ("Aşure","tatli","9a5a3a","d8402a","pudding"),("Güllaç","tatli","f6f2ee","d8402a"),
 ("Tahin Helvası","tatli","d8c8a8","8a6a4a","cheese"),("İrmik Helvası","tatli","e8c070","f2e8c8","dome"),
 ("Un Helvası","tatli","d8a860","f2e0b0","dome"),("Lokum","tatli","f080a8","f6f6f6","lokum"),
 ("Fıstıklı Lokum","tatli","f6f2e8","5a9a3a","lokum"),("Kabak Tatlısı","tatli","e87a20","8a5a2a"),
 ("Ayva Tatlısı","tatli","d8401e","f6f2e6"),("Keşkül","tatli","f6eccc","5a9a3a","pudding"),
 ("Muhallebi","tatli","f8f6ee","d8402a","pudding"),("Höşmerim","tatli","f2d890","f6f0e0","pudding"),
 ("Katmer","tatli","f0c870","4f9a3a","baklava"),("Halka Tatlısı","tatli","e8a030","f6e0a0","simit"),
 ("Kalburabastı","tatli","e09a30","8a5a2a","bun"),("Trileçe","tatli","f2e2b8","b86a2a"),
 ("Profiterol","tatli","4a2a1a","f2e2b8","balls"),("Supangle","tatli","4a2a1a","f2f0e8","pudding"),
 ("Pişmaniye","tatli","f6f0e0","e8d8b0","nest"),("Cezerye","tatli","e8782a","f6f2e6","lokum"),
 ("Kemalpaşa Tatlısı","tatli","e8a840","f6f0e0","balls"),("Peynir Tatlısı","tatli","f0c050","f6f0e0","balls"),
 ("Şöbiyet","tatli","e8b050","4f9a3a","baklava"),("Saray Sarması","tatli","e8b050","4f9a3a","cigars"),
 ("Zerde","tatli","f6c020","d8402a","pudding"),("Kazan Dibi Dondurmalı","tatli","f2e4c4","f6f6f6"),
 ("Hurma Tatlısı","tatli","e09a30","8a5a2a","bun"),("Kurabiye","tatli","e8c070","8a5a2a","bun"),
 ("San Sebastian","tatli","5a3a1a","f2d890","slice"),("Tiramisu","tatli","e8d8b8","5a3a1a","slice"),
 ("Maraş Dondurması","tatli","f6f4ee","d8c8a8","cone"),("Fıstıklı Dondurma","tatli","b8d890","f6f4ee","cone"),
 ("Kaymaklı Dondurma","tatli","f8f6ee","f2e8c8","cone"),("Çikolatalı Dondurma","tatli","6a3a1a","f6f4ee","cone"),
 # --- içecekler
 ("Ayran","icecek","f8f8f4","ffffff","ayran"),("Türk Çayı","icecek","b8301c","f2f0e8","tea"),
 ("Şalgam","icecek","8a1a3a","f6f0e8"),("Boza","icecek","f0d890","e8c070","cup"),
 ("Sahlep","icecek","f6ecd8","b8783a","cup"),("Limonata","icecek","f6e870","f8f8f0"),
 ("Vişne Şerbeti","icecek","9a1a2a","f6f0e8"),("Gül Şerbeti","icecek","f080a0","f6f0e8"),
 ("Kefir","icecek","f6f6f2","e8e8e0"),("Meyan Şerbeti","icecek","4a2a1a","8a5a3a"),
 ("Demirhindi Şerbeti","icecek","6a3a1a","b8783a"),("Kuşburnu Çayı","icecek","d8402a","f6f0e8","tea"),
 ("Ihlamur","icecek","e8b850","f6f0e8","tea"),("Ada Çayı","icecek","b8a040","6a9a3a","tea"),
 ("Elma Çayı","icecek","d8802a","f6f0e8","tea"),("Menengiç Kahvesi","icecek","8a6a4a","f2e8c8","cup"),
 ("Dibek Kahvesi","icecek","5a3a2a","d8c8a8","cup"),("Kenger Kahvesi","icecek","7a5a3a","f2e8c8","cup"),
 ("Türk Kahvesi Fincanı","icecek","3a2418","d8c098","cup"),("Nane Limon","icecek","c8d880","6a9a3a","tea"),
 ("Süt","icecek","fbfbf8","e8e8e0"),("Portakal Suyu","icecek","f8a020","f8f0d0"),
 ("Nar Suyu","icecek","a8142a","f6f0e8"),("Maden Suyu","icecek","d8f0f8","f8f8f8"),
("Su","icecek","bfe3f5","f8f8f8"),
 ("Soda","icecek","e0f4f8","f8f8f8"),("Kayısı Suyu","icecek","f0a030","f8f0d0"),
 # --- kuruyemiş & şekerleme
 ("Leblebi","kuru","e8c870","d8b060"),("Ay Çekirdeği","kuru","3a3a3a","e8e8e0"),
 ("Kabak Çekirdeği","kuru","f2ecd0","d8d0b0"),("Antep Fıstığı","kuru","b8c870","c8a870"),
 ("Fındık","kuru","9a5a2a","d8a060"),("Ceviz","kuru","b88a5a","7a5a3a"),
 ("Kuru İncir","kuru","8a5a3a","c8a070"),("Kuru Kayısı","kuru","f09a30","e8802a"),
 ("Cevizli Sucuk","kuru","8a2a2a","b88a5a","sausage"),("Pestil","kuru","9a3a2a","c85a3a","cheese"),
 ("Kestane Şekeri","kuru","6a3a1a","f6e8c8"),("Akide Şekeri","kuru","e84a6a","f6f0e8","lokum"),
 ("Pamuk Şeker","kuru","f8a0c8","f8f0f6","nest"),("Kuru Üzüm","kuru","5a2a3a","8a4a5a"),
 ("Badem","kuru","c8905a","e8c8a0"),("Kavrulmuş Nohut","kuru","d8a850","b8803a"),
]

# table-ware: key -> (name, base item, shape, lore)
TOOLS = {
    "tabak": ("Tabak", "bowl", "plate_empty", "Ana elinde tut, yemek sol elinde: sağ tıkla = tabağa koy"),
    "kasik": ("Kaşık", "stick", "spoon", "Sol elinde tut, tabaktaki yemeğe sağ tıkla = ye"),
    "catal": ("Çatal", "stick", "fork", "Sol elinde tut, tabaktaki yemeğe sağ tıkla = ye"),
    "bicak": ("Bıçak", "stick", "knife", "Sol elinde tut, tabaktaki yemeğe sağ tıkla = ye"),
}

def tool_snbt(key, count):
    name, base, _, lore = TOOLS[key]
    return (f'{{id:"minecraft:{base}",count:{count},components:{{'
            f'"minecraft:custom_name":{{text:"{name}",color:"white",bold:true,italic:false}},'
            f'"minecraft:lore":[{{text:"{lore}",color:"gray",italic:false}}],'
            f'"minecraft:custom_model_data":{{strings:["{key}"]}},"minecraft:custom_data":{{astro_tool:"{key}"}}}}}}')

# ----------------------------------------------------------------------------- tiny png writer
def png(path, px):
    w = h = 16
    raw = b"".join(b"\x00" + bytes([c for p in px[y] for c in p]) for y in range(h))
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    return data

def rgb(h): return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
def shade(c, f): return tuple(max(0, min(255, int(v * f))) for v in c)
def mix(a, b, t): return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))

class Img:
    def __init__(s, seed):
        s.p = [[(0, 0, 0, 0)] * 16 for _ in range(16)]
        s.seed = seed
    def rnd(s, i):
        x = (s.seed * 2654435761 + i * 40503) & 0xffffffff
        x ^= x >> 13; x = (x * 1274126177) & 0xffffffff
        return (x & 0xffff) / 65535.0
    def set(s, x, y, c):
        if 0 <= x < 16 and 0 <= y < 16: s.p[y][x] = (c[0], c[1], c[2], 255)
    def get(s, x, y): return s.p[y][x] if 0 <= x < 16 and 0 <= y < 16 else (0, 0, 0, 0)
    def ellipse(s, cx, cy, rx, ry, c, light=None, dark=None):
        for y in range(16):
            for x in range(16):
                d = ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2
                if d <= 1:
                    col = c
                    if light and (y + .5 - cy) < -ry * .35 and (x + .5 - cx) < 0: col = light
                    if dark and (y + .5 - cy) > ry * .45: col = dark
                    s.set(x, y, col)
    def rect(s, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): s.set(x, y, c)
    def outline(s):
        out = [row[:] for row in s.p]
        for y in range(16):
            for x in range(16):
                if s.p[y][x][3] == 0:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        n = s.get(x + dx, y + dy)
                        if n[3]:
                            d = shade(n, 0.45); out[y][x] = (d[0], d[1], d[2], 255); break
        # pixels outside the 16x16 are clipped, keep everything in frame
        s.p = out
    def speckle(s, n, c, region, salt=0):
        x0, y0, x1, y1 = region
        for i in range(n):
            x = x0 + int(s.rnd(i * 2 + salt) * (x1 - x0 + 1))
            y = y0 + int(s.rnd(i * 2 + 1 + salt) * (y1 - y0 + 1))
            if s.get(x, y)[3]: s.set(x, y, c)

WHITE = (246, 244, 238); PLATE_D = (196, 196, 206); WOOD = (150, 98, 52); CLAY = (176, 92, 52)

def plate(im):
    im.ellipse(8, 11.2, 7.5, 3.6, WHITE, dark=PLATE_D)
    im.ellipse(8, 10.8, 5.5, 2.4, (234, 232, 228))

def draw(shape, a, b, seed):
    im = Img(seed)
    la, da, lb = mix(a, (255, 255, 255), .35), shade(a, .7), mix(b, (255, 255, 255), .3)
    if shape == "bowl":
        im.ellipse(8, 9.5, 7, 5.5, (236, 232, 224), dark=(200, 196, 190))
        im.rect(1, 6, 14, 8, (236, 232, 224))
        im.ellipse(8, 7, 6.5, 2.4, a, light=la)
        im.speckle(4, b, (4, 6, 11, 8), 3); im.speckle(3, lb, (4, 6, 11, 8), 9)
        im.rect(5, 14, 10, 14, (180, 176, 170))
    elif shape == "pot":
        im.ellipse(8, 10, 7, 5, CLAY, dark=shade(CLAY, .7))
        im.rect(1, 6, 14, 9, CLAY)
        im.ellipse(8, 6.5, 6.2, 2.2, a, light=la)
        im.speckle(5, b, (3, 5, 12, 8), 5)
        im.rect(0, 7, 0, 8, shade(CLAY, .8)); im.rect(15, 7, 15, 8, shade(CLAY, .8))
    elif shape in ("plate", "kebapplate"):
        plate(im)
        if shape == "kebapplate":
            for i in range(4): im.rect(3 + i * 2, 8 - (i % 2), 4 + i * 2, 11, a if i % 2 == 0 else da)
            im.rect(3, 11, 12, 11, b); im.speckle(4, (80, 150, 60), (2, 9, 13, 12), 7)
        else:
            im.ellipse(8, 9.6, 4.6, 2.6, a, light=la, dark=da)
            im.speckle(7, b, (4, 8, 12, 11), 2); im.speckle(3, lb, (4, 8, 12, 11), 11)
    elif shape == "skewer":
        for i in range(16): im.set(i, 15 - i, (168, 168, 176)) if 0 <= 15 - i < 16 else None
        for k, (cx, cy) in enumerate(((4, 11), (7, 8), (10, 5), (13, 2))):
            c = a if k % 2 == 0 else b
            im.ellipse(cx, cy + .5, 2.2, 2.2, c, light=mix(c, (255, 255, 255), .3), dark=shade(c, .7))
    elif shape == "doner":
        im.rect(6, 1, 9, 14, (160, 160, 170))
        im.ellipse(8, 7.5, 4.5, 6.5, a, light=la, dark=da)
        for y in range(2, 14, 2): im.rect(4, y, 11, y, da)
        im.speckle(6, b, (4, 2, 11, 13), 4); im.rect(5, 15, 10, 15, (120, 120, 130))
    elif shape == "drumstick":
        plate(im)
        im.ellipse(6.5, 8.5, 4, 3, a, light=la, dark=da)
        im.rect(9, 7, 12, 8, (240, 234, 220)); im.rect(12, 6, 13, 6, (240, 234, 220)); im.rect(12, 9, 13, 9, (240, 234, 220))
        im.speckle(3, b, (4, 7, 9, 10), 2)
    elif shape == "chop":
        plate(im); im.ellipse(8, 8.5, 4.5, 3, a, light=la, dark=da); im.rect(11, 5, 14, 6, b)
    elif shape == "balls":
        plate(im)
        for cx, cy in ((5, 9), (8, 10), (11, 9), (6.5, 7.2), (9.5, 7.2)):
            im.ellipse(cx, cy, 2, 1.8, a, light=la, dark=da)
        im.speckle(3, b, (3, 6, 13, 12), 6)
    elif shape == "drops":
        plate(im)
        for cx in (5, 8.5, 12): im.ellipse(cx, 8.5, 1.7, 2.8, a, light=la, dark=da)
    elif shape in ("pide", "gozleme"):
        if shape == "pide":
            im.ellipse(8, 8, 7.5, 4, a, light=la, dark=da); im.ellipse(8, 8, 5.2, 2.2, b, light=lb)
            im.speckle(6, shade(b, .7), (4, 7, 12, 9), 1); im.speckle(3, (90, 160, 60), (4, 7, 12, 9), 8)
        else:
            im.rect(2, 4, 13, 12, a); im.rect(2, 4, 13, 4, la); im.rect(2, 12, 13, 12, da)
            im.speckle(10, shade(a, .75), (3, 5, 12, 11), 3); im.speckle(4, b, (3, 5, 12, 11), 9)
            for x in range(3, 13, 3): im.set(x, 8, b)
    elif shape == "lahmacun":
        im.ellipse(8, 8, 7.4, 7.4, a, dark=da); im.ellipse(8, 8, 6, 6, b)
        im.speckle(12, shade(b, .7), (3, 3, 12, 12), 2); im.speckle(5, (90, 160, 60), (3, 3, 12, 12), 7)
        im.rect(7, 5, 8, 11, (240, 236, 200)) if seed % 3 == 0 else None
    elif shape == "borek":
        im.rect(1, 5, 14, 12, a); im.rect(1, 5, 14, 6, la); im.rect(1, 12, 14, 12, da)
        for y in (8, 10): im.rect(1, y, 14, y, b)
        im.speckle(8, shade(a, .8), (2, 5, 13, 6), 5)
    elif shape == "cigars":
        for k, y in enumerate((5, 8, 11)):
            im.ellipse(8 + (k - 1), y + .5, 6.5, 1.5, a, light=la, dark=da)
            im.set(2 + k, y, b); im.set(13 - k, y, b)
    elif shape in ("bun", "loaf"):
        if shape == "bun":
            for cx, cy in ((5.5, 9.5), (10.5, 9.5), (8, 6.5)):
                im.ellipse(cx, cy, 3.4, 3, a, light=la, dark=da)
            im.speckle(5, b, (3, 4, 13, 12), 2)
        else:
            im.ellipse(8, 9, 7.4, 4.8, a, light=la, dark=da)
            for x in (4, 7, 10): im.rect(x, 6, x + 1, 6, b)
    elif shape == "manti":
        im.ellipse(8, 9, 7.4, 5.5, (236, 232, 224), dark=(200, 196, 190))
        im.ellipse(8, 8, 6, 3.6, (246, 244, 236))
        for i in range(7):
            x = 3 + int(im.rnd(i) * 10); y = 6 + int(im.rnd(i + 20) * 4)
            im.rect(x, y, x + 1, y, a)
        im.speckle(8, b, (3, 5, 12, 10), 4); im.speckle(4, (200, 40, 30), (4, 6, 11, 10), 9)
    elif shape == "toast":
        im.rect(2, 3, 13, 12, a); im.rect(2, 3, 13, 3, la); im.rect(2, 12, 13, 12, da)
        for x in range(3, 13, 2): im.set(x, 7 + (x % 3), shade(a, .6))
        im.rect(3, 13, 12, 13, b)
    elif shape == "simit":
        im.ellipse(8, 8, 7, 6.5, a, light=la, dark=da); im.ellipse(8, 8, 3, 2.6, (0, 0, 0))
        for y in range(16):
            for x in range(16):
                if im.p[y][x][:3] == (0, 0, 0): im.p[y][x] = (0, 0, 0, 0)
        im.speckle(14, b, (1, 1, 14, 14), 6)
    elif shape == "round":
        im.ellipse(8, 8.5, 7.3, 5.8, a, light=la, dark=da)
        im.speckle(8, b, (2, 4, 13, 12), 3); im.speckle(4, shade(a, .7), (2, 4, 13, 12), 13)
    elif shape == "sandwich":
        im.ellipse(8, 6, 7, 3, a, light=la); im.rect(1, 7, 14, 8, b); im.rect(1, 9, 14, 9, (90, 160, 60))
        im.ellipse(8, 11, 7, 2.4, a, dark=da)
    elif shape == "pan":
        im.rect(11, 9, 15, 10, (60, 60, 66))
        im.ellipse(7, 9, 6.8, 5.6, (70, 70, 78)); im.ellipse(7, 8.6, 5.8, 4.6, a, light=la)
        im.speckle(9, b, (2, 5, 12, 12), 2)
    elif shape == "cheese":
        for y in range(5, 13):
            x1 = 2 + int((y - 5) * 1.6)
            im.rect(2, y, min(14, x1 + 4), y, a if y > 6 else la)
        im.rect(2, 12, 14, 12, shade(a, .78)); im.speckle(3, b, (3, 7, 12, 11), 5)
    elif shape == "olives":
        plate(im)
        for cx, cy in ((5, 9), (8, 10.5), (11, 9), (7, 7.5), (10, 7.3)):
            im.ellipse(cx, cy, 1.7, 1.4, a, light=b)
    elif shape == "sausage":
        for i in range(12):
            x = 2 + i; y = int(9 - 4 * (1 - ((i - 5.5) / 6) ** 2))
            im.rect(x, y, x, y + 3, a); im.set(x, y, mix(a, (255, 255, 255), .3))
        im.speckle(6, b, (2, 5, 13, 12), 1)
    elif shape == "egg":
        im.ellipse(8, 8.5, 5.5, 6.5, a, dark=shade(a, .85)); im.ellipse(8, 9, 2.6, 2.6, b)
    elif shape == "jar":
        im.rect(4, 2, 11, 3, (120, 120, 130)); im.rect(3, 4, 12, 14, (200, 230, 230))
        im.rect(4, 6, 11, 13, a); im.speckle(10, b, (4, 6, 11, 13), 2); im.rect(4, 5, 4, 13, (230, 250, 250))
    elif shape == "rolls":
        plate(im)
        for k, (cx, cy) in enumerate(((5, 9.5), (8, 10.2), (11, 9.5), (6.5, 7.4), (9.5, 7.4))):
            im.ellipse(cx, cy, 2.4, 1.3, a, light=mix(a, (255, 255, 255), .3), dark=shade(a, .7))
        im.speckle(3, b, (3, 7, 13, 11), 3)
    elif shape == "stuffed":
        plate(im)
        im.ellipse(6, 8.8, 3.4, 3.2, a, light=la, dark=da); im.ellipse(11, 9.2, 3.2, 3, a, light=la, dark=da)
        im.ellipse(6, 6.4, 2.2, 1, b); im.ellipse(11, 6.8, 2, 1, b); im.set(6, 4, (80, 150, 60))
    elif shape == "mussel":
        plate(im)
        for cx, cy in ((5, 9.5), (10.5, 9.5), (7.8, 7)):
            im.ellipse(cx, cy, 3, 2, a); im.ellipse(cx, cy - .3, 2, 1.1, b)
    elif shape in ("rice", "dome"):
        plate(im)
        if shape == "dome": im.ellipse(8, 7.8, 4.8, 4.4, a, light=la, dark=da)
        else: im.ellipse(8, 9, 5.2, 3, a, light=la)
        im.speckle(10, b if shape == "dome" else shade(a, .85), (3, 5, 13, 11), 6)
        im.speckle(4, b, (4, 6, 12, 10), 15)
    elif shape == "noodles":
        plate(im)
        for i in range(5):
            y = 7 + i
            for x in range(3, 13):
                if (x + i + seed) % 3: im.set(x, y + (1 if (x + i) % 4 == 0 else 0), a if (x + i) % 2 else shade(a, .82))
        im.ellipse(8, 7.5, 2.5, 1.5, b, light=lb)
    elif shape == "fish":
        plate(im)
        im.ellipse(7, 8.8, 5, 2.4, a, light=la, dark=da)
        im.rect(12, 7, 13, 10, da); im.rect(14, 6, 14, 11, da); im.set(3, 8, (20, 20, 20))
        im.rect(5, 8, 9, 8, b)
    elif shape == "rings":
        plate(im)
        for cx, cy in ((5, 9), (9, 10), (11, 8), (7, 7.3)):
            im.ellipse(cx, cy, 2.2, 1.6, a, dark=shade(a, .75)); im.set(int(cx), int(cy), (234, 232, 228))
    elif shape == "wrap":
        for i in range(10):
            im.rect(4 + i // 2, 2 + i, 11 + i // 3, 2 + i, a)
        im.rect(5, 2, 11, 3, b); im.speckle(5, (90, 160, 60), (5, 2, 11, 3), 4)
        im.rect(5, 12, 13, 14, (220, 220, 225)); im.rect(5, 12, 13, 12, (250, 250, 250))
    elif shape == "kumpir":
        im.ellipse(8, 10, 7, 4.6, (200, 200, 208), dark=(160, 160, 170))
        im.ellipse(8, 7.6, 5.6, 3.6, a, light=la, dark=da)
        im.speckle(10, b, (3, 5, 12, 10), 2); im.speckle(6, (200, 50, 40), (3, 5, 12, 10), 9)
        im.speckle(5, (90, 160, 60), (3, 5, 12, 10), 17)
    elif shape == "burger":
        im.ellipse(8, 6, 7, 3.2, a, light=la); im.rect(1, 8, 14, 9, b); im.rect(2, 10, 13, 10, (200, 40, 30))
        im.ellipse(8, 11.8, 6.8, 2, shade(a, .85))
    elif shape == "corn":
        im.ellipse(8, 8, 3.4, 7, a, dark=da)
        for y in range(2, 14, 2):
            for x in range(6, 11, 2): im.set(x, y, mix(a, (255, 255, 255), .35))
        im.rect(7, 14, 9, 15, b)
    elif shape == "nuts":
        for i in range(14):
            cx = 2.5 + im.rnd(i) * 11; cy = 5 + im.rnd(i + 50) * 8
            im.ellipse(cx, cy, 1.6, 1.3, a if i % 3 else b)
    elif shape == "baklava":
        for k, (cx, cy) in enumerate(((5, 10), (11, 10), (8, 6))):
            for y in range(-3, 4):
                w = 3 - abs(y)
                for x in range(-w, w + 1):
                    c = la if y < 0 else (a if y == 0 else da)
                    im.set(int(cx + x), int(cy + y), c)
            im.set(int(cx), int(cy) - 1, b); im.set(int(cx), int(cy), b)
    elif shape == "nest":
        im.ellipse(8, 9, 6.8, 5.2, a, dark=da)
        for i in range(30):
            x = 2 + int(im.rnd(i) * 12); y = 4 + int(im.rnd(i + 70) * 9)
            if im.get(x, y)[3]: im.set(x, y, la if i % 2 else shade(a, .8))
        im.ellipse(8, 8, 2.2, 1.6, b)
    elif shape == "pudding":
        im.ellipse(8, 10.5, 6.5, 4.5, (238, 236, 230), dark=(205, 200, 195))
        im.rect(2, 6, 13, 9, (238, 236, 230))
        im.ellipse(8, 6.5, 5.6, 2, a, light=la)
        im.speckle(5, b, (4, 5, 11, 7), 5)
    elif shape == "lokum":
        for k, (x0, y0) in enumerate(((2, 8), (8, 8), (5, 3))):
            c = a if k != 1 else mix(a, b, .5)
            im.rect(x0, y0, x0 + 5, y0 + 5, c); im.rect(x0, y0, x0 + 5, y0, mix(c, (255, 255, 255), .5))
            im.speckle(4, (255, 255, 255), (x0, y0, x0 + 5, y0 + 5), k * 7)
            im.speckle(2, b, (x0 + 1, y0 + 1, x0 + 4, y0 + 4), k * 9 + 3)
    elif shape == "slice":
        for y in range(4, 13):
            x1 = 3 + int((y - 4) * 1.2)
            im.rect(3, y, min(13, x1 + 3), y, a)
        im.rect(3, 4, 6, 5, b); im.rect(3, 12, 13, 13, shade(a, .7)); im.speckle(4, b, (3, 6, 12, 11), 5)
    elif shape == "cone":
        for y in range(8, 16):
            w = int((15 - y) * .6)
            im.rect(8 - w, y, 8 + w, y, (210, 150, 70) if (y % 2) else (180, 120, 50))
        im.ellipse(8, 5.5, 4.5, 4, a, light=la, dark=da); im.ellipse(8, 2.5, 2.5, 2, b)
    elif shape == "glass":
        im.rect(4, 2, 11, 14, (210, 235, 240)); im.rect(5, 4, 10, 13, a); im.rect(5, 4, 10, 4, mix(a, (255, 255, 255), .4))
        im.rect(4, 2, 4, 14, (235, 250, 252)); im.rect(4, 14, 11, 14, (170, 200, 210))
    elif shape == "ayran":
        im.rect(4, 2, 11, 14, (215, 235, 240)); im.rect(5, 3, 10, 13, a)
        for x in range(5, 11): im.set(x, 3, (255, 255, 255)); im.set(x, 2, (255, 255, 255)) if x % 2 else None
        im.rect(4, 2, 4, 14, (238, 250, 252)); im.rect(4, 14, 11, 14, (180, 205, 215))
        im.speckle(5, (235, 235, 230), (5, 4, 10, 12), 3)
    elif shape == "tea":
        im.ellipse(8, 14.6, 6, 1.2, (200, 200, 210))
        for y in range(2, 14):
            w = 3 if y < 5 else (2 if y < 9 else 3)
            im.rect(8 - w, y, 7 + w, y, (225, 240, 245))
        for y in range(4, 13):
            w = 2 if y < 5 else (1 if y < 9 else 2)
            im.rect(8 - w, y, 7 + w, y, a)
        im.rect(5, 2, 10, 2, (240, 250, 252))
    elif shape == "cup":
        im.ellipse(8, 14, 6.5, 1.6, (230, 230, 236))
        im.rect(4, 5, 11, 12, (240, 238, 232)); im.rect(12, 7, 13, 10, (240, 238, 232))
        im.ellipse(7.5, 5.5, 3.6, 1.3, a, light=b); im.rect(4, 12, 11, 12, (210, 206, 200))
        im.set(6, 8, (200, 40, 40)); im.set(9, 9, (40, 90, 200))
    elif shape == "plate_empty":
        im.ellipse(8, 9, 7.6, 4.6, WHITE, dark=PLATE_D)
        im.ellipse(8, 8.6, 5.4, 3, (232, 230, 226)); im.ellipse(8, 8.4, 3.6, 1.8, (240, 238, 234))
        for x in range(2, 15, 3): im.set(x, 9 if x in (2, 14) else 6 if x == 8 else 7, (40, 90, 170))
    elif shape == "spoon":
        for i in range(9): im.set(3 + i, 13 - i, (200, 200, 210)); im.set(4 + i, 13 - i, (170, 170, 182))
        im.ellipse(12.2, 3.8, 2.4, 2.8, (215, 215, 225), light=(245, 245, 250), dark=(160, 160, 172))
    elif shape == "fork":
        for i in range(8): im.set(3 + i, 13 - i, (200, 200, 210)); im.set(4 + i, 13 - i, (170, 170, 182))
        im.rect(10, 4, 12, 6, (205, 205, 215))
        for k in range(3): im.set(11 + k, 2 + k, (220, 220, 230)); im.set(10 + k, 1 + k, (220, 220, 230)) if k < 2 else None
        im.set(13, 2, (220, 220, 230)); im.set(12, 1, (220, 220, 230)); im.set(14, 3, (220, 220, 230))
    elif shape == "knife":
        for i in range(5): im.rect(2 + i, 13 - i, 3 + i, 13 - i, (110, 70, 40))
        for i in range(8):
            im.set(7 + i, 8 - i, (225, 225, 235)); im.set(7 + i, 9 - i, (195, 195, 205)); im.set(8 + i, 9 - i, (160, 160, 172))
    im.outline()
    return im.p

# ----------------------------------------------------------------------------- outputs
TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
def slug(n): return re.sub(r"[^a-z0-9]+", "_", n.translate(TR).lower()).strip("_")

def esc(s): return s.replace("\\", "\\\\").replace('"', '\\"')

def item_snbt(name, cat, sid):
    label, base, nut, sat, _, color, rem = CATS[cat]
    drink = cat == "icecek"
    comps = [
        f'"minecraft:custom_name":{{text:"{esc(name)}",color:"{color}",bold:true,italic:false}}',
        f'"minecraft:lore":[{{text:"{esc(label)}",color:"gray",italic:false}},{{text:"Astro Türk Mutfağı",color:"dark_gray",italic:true}}]',
        f'"minecraft:custom_model_data":{{strings:["{sid}"]}}',
        f'"minecraft:custom_data":{{astro_food:"{sid}"}}',
        '"minecraft:max_stack_size":64',
        f'"minecraft:food":{{nutrition:{nut},saturation:{sat}f,can_always_eat:{"true" if drink else "false"}}}',
        '"minecraft:consumable":{consume_seconds:%sf,animation:"%s",sound:"minecraft:%s",has_consume_particles:%s}'
        % ("1.2" if drink else "1.6", "drink" if drink else "eat",
           "entity.generic.drink" if drink else "entity.generic.eat", "false" if drink else "true"),
    ]
    if rem: comps.append(f'"minecraft:use_remainder":{{id:"minecraft:{rem}",count:1}}')
    return f'{{id:"minecraft:{base}",count:16,components:{{{",".join(comps)}}}}}'

def main():
    seen = set(); foods = []
    for row in F:
        name, cat, a, b = row[:4]; shape = row[4] if len(row) > 4 else CATS[cat][4]
        sid = slug(name)
        if sid in seen: continue
        seen.add(sid); foods.append((name, cat, a, b, shape, sid))

    # ---- resource pack
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    pack = os.path.join(ROOT, "build", "astro_food_pack.zip")
    by_base = {}
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pack.mcmeta", json.dumps({"pack": {"description": "Astro SMP - Türk Mutfağı",
                   "pack_format": 69, "min_format": 69, "max_format": 9999}}, ensure_ascii=False, indent=1))
        for i, (name, cat, a, b, shape, sid) in enumerate(foods):
            px = draw(shape, rgb(a), rgb(b), i + 7)
            z.writestr(f"assets/astro/textures/item/food/{sid}.png", png(None, px))
            z.writestr(f"assets/astro/models/item/food/{sid}.json",
                       json.dumps({"parent": "minecraft:item/generated", "textures": {"layer0": f"astro:item/food/{sid}"}}))
            by_base.setdefault(CATS[cat][1], []).append(sid)
        for j, (key, (tname, tbase, tshape, _)) in enumerate(TOOLS.items()):
            z.writestr(f"assets/astro/textures/item/food/{key}.png", png(None, draw(tshape, (240, 240, 240), (200, 200, 200), 900 + j)))
            z.writestr(f"assets/astro/models/item/food/{key}.json",
                       json.dumps({"parent": "minecraft:item/handheld" if tbase == "stick" else "minecraft:item/generated",
                                   "textures": {"layer0": f"astro:item/food/{key}"}}))
            by_base.setdefault(tbase, []).append(key)
        for base, sids in by_base.items():
            z.writestr(f"assets/minecraft/items/{base}.json", json.dumps({"model": {
                "type": "minecraft:select", "property": "minecraft:custom_model_data", "index": 0,
                "cases": [{"when": s, "model": {"type": "minecraft:model", "model": f"astro:item/food/{s}"}} for s in sids],
                "fallback": {"type": "minecraft:model", "model": f"minecraft:item/{base}"}}}))
    # ---- tell the mod where the pack lives (exact release tag) + its sha1
    run = os.environ.get("GITHUB_RUN_NUMBER", "dev")
    repo = os.environ.get("GITHUB_REPOSITORY", "ulucyamanavciyaman-byte/astro-staff")
    sha1 = hashlib.sha1(open(pack, "rb").read()).hexdigest()
    url = f"https://github.com/{repo}/releases/download/build-{run}/astro_food_pack.zip"
    open(os.path.join(ROOT, "src", "main", "resources", "astro_pack.txt"), "w").write(f"{url} {sha1}\n")
    # ---- spawn function: 2 chests in front of the player, filled with one shulker per category
    boxes = []
    colors = ["orange", "red", "brown", "yellow", "white", "lime", "green", "purple", "light_blue",
              "cyan", "blue", "pink", "magenta", "light_gray", "gray", "black"]
    for ci, (cat, meta) in enumerate(CATS.items()):
        items = [f for f in foods if f[1] == cat]
        for part in range(0, len(items), 27):
            chunk = items[part:part + 27]
            title = meta[0] + (f" {part // 27 + 1}" if len(items) > 27 else "")
            content = ",".join(f'{{slot:{k},item:{item_snbt(n, c, s)}}}' for k, (n, c, a, b, sh, s) in enumerate(chunk))
            boxes.append(f'minecraft:{colors[ci % len(colors)]}_shulker_box[custom_name={{text:"{esc(title)}",color:"gold",bold:true,italic:false}},container=[{content}]]')
    ware = [tool_snbt("tabak", 64), tool_snbt("tabak", 64), tool_snbt("kasik", 16), tool_snbt("catal", 16), tool_snbt("bicak", 16)]
    content = ",".join(f'{{slot:{k},item:{it}}}' for k, it in enumerate(ware))
    boxes.insert(0, f'minecraft:white_shulker_box[custom_name={{text:"Sofra Takımı (Tabak, Kaşık, Çatal, Bıçak)",color:"gold",bold:true,italic:false}},container=[{content}]]')
    half = (len(boxes) + 1) // 2
    lines = ["# generated by tools/turk_food.py - do not edit by hand",
             'execute rotated ~ 0 positioned ^1 ^ ^2 run setblock ~ ~ ~ minecraft:chest{CustomName:{text:"Türk Mutfağı 1",color:"gold",bold:true}} replace',
             'execute rotated ~ 0 positioned ^-1 ^ ^2 run setblock ~ ~ ~ minecraft:chest{CustomName:{text:"Türk Mutfağı 2",color:"gold",bold:true}} replace']
    for i, box in enumerate(boxes):
        side, slot = ("^1", i) if i < half else ("^-1", i - half)
        lines.append(f"execute rotated ~ 0 positioned {side} ^ ^2 run item replace block ~ ~ ~ container.{slot} with {box}")
    lines += ['playsound minecraft:block.chest.open master @a ~ ~ ~ 1 1',
              'particle minecraft:happy_villager ~ ~1 ~ 1 0.5 1 0 20',
              f'tellraw @s [{{"text":"🍽 Afiyet olsun! ","color":"gold","bold":true}},{{"text":"{len(foods)} Türk yemeği önündeki 2 sandıkta.","color":"yellow"}}]']
    fdir = os.path.join(ROOT, "src", "main", "resources", "data", "astro_staff", "function", "turk")
    os.makedirs(fdir, exist_ok=True)
    open(os.path.join(fdir, "spawn.mcfunction"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"{len(foods)} foods, {len(boxes)} shulker boxes, pack {os.path.getsize(pack)} bytes")
    return foods

if __name__ == "__main__":
    main()
