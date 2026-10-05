#!/usr/bin/env python3
"""OpenStreetMap (Overpass API) üzerinden Türkiye'deki araç kiralama
noktalarını tarar ve il il ham sonuçları data/ham/osm/ altına yazar.

Tek bir ülke geneli sorgu yapılır; sonuçlar Overpass tarafında 81 ilin
sınırlarına göre gruplanır (il başına ayrı sorgudan çok daha hızlıdır).

Kullanım:
    python3 scripts/tara_osm.py              # 81 ilin tamamı
    python3 scripts/tara_osm.py 34 6 35      # yalnızca belirtilen plakaların dosyaları güncellenir

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

# "car_rental" OSM'deki standart etikettir; isminde "rent a car" vb. geçen
# ama yanlış etiketlenmiş işletmeler de isim filtresiyle yakalanır.
# Her ilin sınır ilişkisi (admin_level=4, ISO3166-2=TR-xx) çıktıda kendi
# kayıtlarından hemen önce yazılır; bu sayede sonuçlar ile eşlenir.
SORGU = """
[out:json][timeout:900];
area["ISO3166-1"="TR"]["admin_level"="2"]->.tr;
(
  nwr["amenity"="car_rental"](area.tr);
  nwr["shop"="car_rental"](area.tr);
  nwr["name"~"rent ?a ?car|araç kiralama|arac kiralama|oto kiralama|car rental",i](area.tr);
)->.hepsi;
rel["boundary"="administrative"]["admin_level"="4"]["ISO3166-2"~"^TR-[0-9]{2}$"](area.tr)->.iller;
foreach.iller->.il(
  .il out tags;
  .il map_to_area->.a;
  nwr.hepsi(area.a);
  out center tags;
);
"""


def overpass(sorgu: str) -> dict:
    veri = urllib.parse.urlencode({"data": sorgu}).encode()
    son_hata = None
    for deneme in range(2):
        for url in OVERPASS_URLS:
            try:
                print(f"  {url} sorgulanıyor...", flush=True)
                istek = urllib.request.Request(url, data=veri, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(istek, timeout=960) as yanit:
                    return json.load(yanit)
            except Exception as hata:  # ağ hatası, 429, 504 ...
                print(f"  hata: {hata}", flush=True)
                son_hata = hata
                time.sleep(10)
        time.sleep(60 * (deneme + 1))
    raise RuntimeError(f"Overpass sorgusu başarısız: {son_hata}")


def il_il_ayir(elemanlar: list[dict]) -> dict[int, list[dict]]:
    gruplar: dict[int, list[dict]] = {}
    plaka = None
    for e in elemanlar:
        t = e.get("tags", {})
        if e["type"] == "relation" and t.get("admin_level") == "4" and t.get("ISO3166-2", "").startswith("TR-"):
            plaka = int(t["ISO3166-2"][3:])
            gruplar.setdefault(plaka, [])
        elif plaka is not None:
            gruplar[plaka].append(e)
    return gruplar


def main(argv):
    plakalar = [int(a) for a in argv] or sorted(ILLER)
    print("Türkiye geneli Overpass sorgusu (birkaç dakika sürebilir)...", flush=True)
    sonuc = overpass(SORGU)
    gruplar = il_il_ayir(sonuc.get("elements", []))
    eksik = sorted(set(ILLER) - set(gruplar))
    if eksik:
        print(f"UYARI: sınırı bulunamayan iller: {eksik}", flush=True)

    HAM_DIZIN.mkdir(parents=True, exist_ok=True)
    zaman = sonuc.get("osm3s", {}).get("timestamp_osm_base", "")
    for plaka in plakalar:
        if plaka not in gruplar:
            continue  # sınırı gelmeyen ilin mevcut dosyasını silme
        hedef = HAM_DIZIN / f"{dosya_adi(plaka)}.json"
        hedef.write_text(json.dumps(
            {"osm_zaman": zaman, "elements": gruplar[plaka]},
            ensure_ascii=False, indent=1,
        ), encoding="utf-8")
        print(f"[{plaka:02d}] {ILLER[plaka]}: {len(gruplar[plaka])} kayıt", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
