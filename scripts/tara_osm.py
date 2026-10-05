#!/usr/bin/env python3
"""OpenStreetMap (Overpass API) üzerinden Türkiye'deki araç kiralama
noktalarını il il tarar ve ham sonuçları data/ham/osm/ altına yazar.

Kullanım:
    python3 scripts/tara_osm.py              # 81 ilin tamamı
    python3 scripts/tara_osm.py 34 6 35      # yalnızca belirtilen plakalar

Veri lisansı: © OpenStreetMap katkıcıları, ODbL 1.0.
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from iller import ILLER, dosya_adi

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
HAM_DIZIN = Path(__file__).resolve().parent.parent / "data" / "ham" / "osm"
USER_AGENT = "rent-a-car-directory/1.0 (github.com/baytemizel/rent-a-car-directory)"

# Araç kiralama ile ilişkili etiketler. "car_rental" OSM'deki standart
# etikettir; isminde "rent a car" geçen ama yanlış etiketlenmiş işletmeler
# de isim filtresiyle yakalanır.
SORGU = """
[out:json][timeout:180];
area["ISO3166-2"="TR-{plaka:02d}"]["admin_level"="4"]->.il;
(
  nwr["amenity"="car_rental"](area.il);
  nwr["shop"="car_rental"](area.il);
  nwr["name"~"rent ?a ?car|araç kiralama|arac kiralama|oto kiralama|car rental",i](area.il);
);
out center tags;
"""


def overpass(sorgu: str) -> dict:
    veri = urllib.parse.urlencode({"data": sorgu}).encode()
    son_hata = None
    for url in OVERPASS_URLS:
        for deneme in range(3):
            try:
                istek = urllib.request.Request(url, data=veri, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(istek, timeout=240) as yanit:
                    return json.load(yanit)
            except Exception as hata:  # ağ hatası, 429, 504 ...
                son_hata = hata
                time.sleep(5 * (deneme + 1))
    raise RuntimeError(f"Overpass sorgusu başarısız: {son_hata}")


def main(argv):
    plakalar = [int(a) for a in argv] or sorted(ILLER)
    HAM_DIZIN.mkdir(parents=True, exist_ok=True)
    for plaka in plakalar:
        print(f"[{plaka:02d}] {ILLER[plaka]} taranıyor...", flush=True)
        sonuc = overpass(SORGU.format(plaka=plaka))
        hedef = HAM_DIZIN / f"{dosya_adi(plaka)}.json"
        hedef.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"      {len(sonuc.get('elements', []))} kayıt -> {hedef.name}")
        time.sleep(2)  # Overpass kullanım kurallarına saygı


if __name__ == "__main__":
    main(sys.argv[1:])
